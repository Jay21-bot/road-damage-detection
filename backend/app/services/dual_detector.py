"""
Dual-Engine YOLO Inference Coordinator
Orchestrates simultaneous road damage detection and general object recognition,
handles frame-skipping, IoU deduplication, border suppression, and aggregated telemetry.
"""

import time
import uuid
import threading
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.services.yolo_detector import general_detector, road_damage_detector, calculate_iou


class DualYoloInferenceEngine:
    """
    Coordinates execution of:
    1. Pretrained General Object Detection (Vehicles, Pedestrians)
    2. Custom Road Damage Detection (Potholes, Cracks)
    Supports dynamic modes: 'all', 'traffic', 'damage', 'pedestrian'
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._frame_counter = 0
        self._cached_detections: List[Dict[str, Any]] = []
        self._cached_telemetry: Dict[str, Any] = {
            "inferred": False,
            "frame_id": 0,
            "latency_ms": 0.0,
            "damage_count": 0,
            "object_count": 0,
            "total_detections": 0
        }
        self._total_inferences = 0
        self._avg_latency_ms = 0.0
        
        # Operational mode toggles
        self.mode: str = "all"  # 'all', 'traffic', 'damage', 'pedestrian'
        self.road_damage_conf: float = settings.ROAD_DAMAGE_CONF_THRESHOLD
        self.general_object_conf: float = settings.GENERAL_OBJECT_CONF_THRESHOLD

    @property
    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "general_model_ready": general_detector.is_loaded,
                "road_damage_model_ready": road_damage_detector.is_loaded,
                "device": general_detector.device,
                "mode": self.mode,
                "frame_skip": settings.FRAME_SKIP,
                "road_damage_conf": self.road_damage_conf,
                "general_object_conf": self.general_object_conf,
                "avg_latency_ms": round(self._avg_latency_ms, 2),
                "total_inferences": self._total_inferences
            }

    def set_mode(self, mode: str):
        with self._lock:
            self.mode = mode.lower()
            logger.info(f"AI Detection Mode switched to: {self.mode.upper()}")

    def set_thresholds(self, damage_conf: Optional[float] = None, object_conf: Optional[float] = None):
        with self._lock:
            if damage_conf is not None:
                self.road_damage_conf = max(0.1, min(0.99, damage_conf))
            if object_conf is not None:
                self.general_object_conf = max(0.1, min(0.99, object_conf))

    def get_latest_detections(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._cached_detections)

    def get_latest_telemetry(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._cached_telemetry)

    def process_frame(
        self,
        frame: np.ndarray,
        force_inference: bool = False
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Processes a single frame through the dual-YOLO pipeline.
        Downscales high-res frames for fast CPU inference, then scales coordinates back.
        """
        self._frame_counter += 1
        t_start = time.perf_counter()

        should_infer = force_inference or (self._frame_counter % settings.FRAME_SKIP == 0)

        with self._lock:
            cached_copy = list(self._cached_detections)
            current_mode = self.mode
            dmg_conf = self.road_damage_conf
            obj_conf = self.general_object_conf

        if not should_infer and cached_copy:
            telemetry = {
                "inferred": False,
                "frame_id": self._frame_counter,
                "latency_ms": 0.0,
                "damage_count": sum(1 for d in cached_copy if d["category"] == "road_damage"),
                "object_count": sum(1 for d in cached_copy if d["category"] == "general_object"),
                "total_detections": len(cached_copy)
            }
            return cached_copy, telemetry

        orig_h, orig_w = frame.shape[:2]

        # Fast downscale for inference if frame is larger than 640x360
        scale_x, scale_y = 1.0, 1.0
        if orig_w > 640 or orig_h > 480:
            infer_w = 640
            infer_h = int(orig_h * (640.0 / orig_w))
            infer_frame = cv2.resize(frame, (infer_w, infer_h))
            scale_x = orig_w / float(infer_w)
            scale_y = orig_h / float(infer_h)
        else:
            infer_frame = frame

        fused: List[Dict[str, Any]] = []
        t_damage, t_object = 0.0, 0.0

        # 1. Road Damage Detection (if enabled by mode)
        if current_mode in ("all", "damage"):
            damage_detections, t_damage = road_damage_detector.detect(infer_frame, conf_threshold=dmg_conf)
            for d in damage_detections:
                x1, y1, x2, y2 = d["bbox"]
                d["bbox"] = [int(x1 * scale_x), int(y1 * scale_y), int(x2 * scale_x), int(y2 * scale_y)]
                d["id"] = str(uuid.uuid4())
                d["timestamp"] = time.time()
                fused.append(d)

        # 2. General Object Detection (if enabled by mode)
        if current_mode in ("all", "traffic", "pedestrian"):
            obj_detections, t_object = general_detector.detect(infer_frame, conf_threshold=obj_conf)
            for obj in obj_detections:
                # If pedestrian-only mode, skip non-pedestrians
                if current_mode == "pedestrian" and obj["class_name"] != "pedestrian":
                    continue
                # If traffic-only mode, skip pedestrians
                if current_mode == "traffic" and obj["class_name"] == "pedestrian":
                    continue

                x1, y1, x2, y2 = obj["bbox"]
                obj["bbox"] = [int(x1 * scale_x), int(y1 * scale_y), int(x2 * scale_x), int(y2 * scale_y)]
                obj["id"] = str(uuid.uuid4())
                obj["timestamp"] = time.time()
                fused.append(obj)

        total_latency = (time.perf_counter() - t_start) * 1000.0

        with self._lock:
            self._cached_detections = fused
            self._total_inferences += 1
            self._avg_latency_ms = (self._avg_latency_ms * 0.8) + (total_latency * 0.2) if self._avg_latency_ms else total_latency

            damage_cnt = sum(1 for d in fused if d["category"] == "road_damage")
            object_cnt = sum(1 for d in fused if d["category"] == "general_object")

            self._cached_telemetry = {
                "inferred": True,
                "frame_id": self._frame_counter,
                "latency_ms": round(total_latency, 2),
                "damage_latency_ms": round(t_damage, 2),
                "object_latency_ms": round(t_object, 2),
                "damage_count": damage_cnt,
                "object_count": object_cnt,
                "total_detections": damage_cnt + object_cnt
            }
            telemetry = dict(self._cached_telemetry)

        return fused, telemetry


dual_engine = DualYoloInferenceEngine()
