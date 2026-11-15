"""
Dual-Engine YOLO Detection Service
Provides dedicated detector classes for General Objects and Custom Road Damages
(Potholes, Longitudinal Cracks, Transverse Cracks, Alligator Cracks).
"""

import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np
import torch
from ultralytics import YOLO

# Optimize PyTorch CPU threading for fast matrix math
try:
    torch.set_num_threads(4)
except Exception:
    pass

from app.core.config import settings
from app.core.logging import logger


def calculate_iou(box1: List[int], box2: List[int]) -> float:
    """Calculates Intersection over Union between two bounding boxes [x1, y1, x2, y2]."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - intersection

    return intersection / union if union > 0 else 0.0


def calculate_ios(box1: List[int], box2: List[int]) -> float:
    """Calculates Intersection over Smaller Area (IoS) to suppress nested/subsumed boxes."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = max(1, (box1[2] - box1[0]) * (box1[3] - box1[1]))
    area2 = max(1, (box2[2] - box2[0]) * (box2[3] - box2[1]))
    return intersection / min(area1, area2)


class GeneralObjectDetector:
    """
    Manages inference for general traffic participants using pretrained YOLO models.
    Strictly filters for road participants: vehicles and pedestrians.
    """

    ROAD_CLASS_FILTER = {
        0: "pedestrian",       # person
        1: "bicycle",          # bicycle
        2: "car",              # car
        3: "motorcycle",       # motorcycle
        5: "bus",              # bus
        7: "truck"             # truck
    }

    def __init__(self, model_path: Optional[str] = None, device: Optional[str] = None):
        self.model_path = model_path or settings.GENERAL_OBJECT_MODEL_PATH
        self.device = self._resolve_device(device or settings.DEVICE)
        self.model: Optional[YOLO] = None
        self._is_loaded = False
        self._load_model()

    def _resolve_device(self, preferred_device: str) -> str:
        if preferred_device.lower() == "cuda":
            if torch.cuda.is_available():
                return "cuda:0"
            logger.warning("CUDA requested but not available. Falling back to CPU.")
            return "cpu"
        elif preferred_device.lower() == "cpu":
            return "cpu"
        return "cuda:0" if torch.cuda.is_available() else "cpu"

    def _load_model(self):
        try:
            logger.info(f"Loading General Object YOLO model from '{self.model_path}' on '{self.device}'...")
            resolved_path = Path(self.model_path)
            if not resolved_path.is_absolute():
                resolved_path = Path(__file__).resolve().parent.parent.parent / self.model_path

            weights_identifier = str(resolved_path) if resolved_path.exists() else "yolov8n.pt"
            self.model = YOLO(weights_identifier)
            self.model.to(self.device)
            self._is_loaded = True
            logger.info(f"General Object Model ready on {self.device}.")
        except Exception as e:
            logger.error(f"Failed to load General Object model: {e}")
            self.model = None
            self._is_loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    def detect(
        self,
        frame: np.ndarray,
        conf_threshold: Optional[float] = None,
        filter_road_classes: bool = True
    ) -> Tuple[List[Dict[str, Any]], float]:
        if not self._is_loaded or self.model is None:
            return [], 0.0

        conf = conf_threshold if conf_threshold is not None else settings.GENERAL_OBJECT_CONF_THRESHOLD
        t0 = time.perf_counter()

        results = self.model.predict(
            source=frame,
            conf=conf,
            iou=0.45,
            device=self.device,
            imgsz=settings.INFERENCE_IMAGE_SIZE,
            verbose=False
        )

        latency_ms = (time.perf_counter() - t0) * 1000.0
        raw_detections: List[Dict[str, Any]] = []

        if not results or len(results) == 0:
            return raw_detections, latency_ms

        result = results[0]
        h, w = frame.shape[:2]

        for box in result.boxes:
            cls_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())

            if filter_road_classes and cls_id not in self.ROAD_CLASS_FILTER:
                continue

            class_name = self.ROAD_CLASS_FILTER.get(cls_id, result.names.get(cls_id, f"obj_{cls_id}"))
            xyxy = box.xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = [int(val) for val in xyxy]

            # Minimum size check to eliminate noise
            if (x2 - x1) < 20 or (y2 - y1) < 20:
                continue

            cx = ((x1 + x2) / 2.0) / w
            cy = ((y1 + y2) / 2.0) / h
            nw = (x2 - x1) / w
            nh = (y2 - y1) / h

            raw_detections.append({
                "category": "general_object",
                "class_id": cls_id,
                "class_name": class_name,
                "confidence": round(confidence, 3),
                "bbox": [x1, y1, x2, y2],
                "normalized_bbox": [round(cx, 4), round(cy, 4), round(nw, 4), round(nh, 4)]
            })

        # Deduplicate with IoU NMS and cap at top-5 cleanest detections
        raw_detections.sort(key=lambda d: d["confidence"], reverse=True)
        clean_detections: List[Dict[str, Any]] = []
        for cand in raw_detections:
            if not any(calculate_iou(cand["bbox"], acc["bbox"]) > 0.35 for acc in clean_detections):
                clean_detections.append(cand)
            if len(clean_detections) >= 5:
                break

        return clean_detections, latency_ms


class RoadDamageDetector:
    """
    Manages custom-trained YOLO model for detecting road surface damages:
    - Potholes (D40)
    - Longitudinal cracks (D00)
    - Transverse cracks (D10)
    - Alligator cracks (D20)
    """

    DAMAGE_CLASSES = {
        0: "longitudinal_crack",
        1: "transverse_crack",
        2: "alligator_crack",
        3: "pothole"
    }

    def __init__(self, model_path: Optional[str] = None, device: Optional[str] = None):
        self.model_path = model_path or settings.ROAD_DAMAGE_MODEL_PATH
        self.device = self._resolve_device(device or settings.DEVICE)
        self.model: Optional[YOLO] = None
        self._is_loaded = False
        self._load_model()

    def _resolve_device(self, preferred_device: str) -> str:
        if preferred_device.lower() == "cuda":
            if torch.cuda.is_available():
                return "cuda:0"
            logger.warning("CUDA requested but not available. Falling back to CPU.")
            return "cpu"
        elif preferred_device.lower() == "cpu":
            return "cpu"
        return "cuda:0" if torch.cuda.is_available() else "cpu"

    def _load_model(self):
        try:
            logger.info(f"Loading Road Damage YOLO model from '{self.model_path}' on '{self.device}'...")
            resolved_path = Path(self.model_path)
            if not resolved_path.is_absolute():
                resolved_path = Path(__file__).resolve().parent.parent.parent / self.model_path

            if not resolved_path.exists():
                logger.warning(
                    f"Road damage weights '{resolved_path}' not found. "
                    "Run scripts/train_road_damage.py to train or initialize weights."
                )
                self.model = None
                self._is_loaded = False
                return

            self.model = YOLO(str(resolved_path))
            self.model.to(self.device)
            self._is_loaded = True
            logger.info(f"Road Damage Model successfully initialized on {self.device}.")
        except Exception as e:
            logger.error(f"Failed to load Road Damage model: {e}")
            self.model = None
            self._is_loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    def detect(
        self,
        frame: np.ndarray,
        conf_threshold: Optional[float] = None
    ) -> Tuple[List[Dict[str, Any]], float]:
        """Executes road damage detection on a single frame."""
        if not self._is_loaded or self.model is None:
            return [], 0.0

        conf = conf_threshold if conf_threshold is not None else settings.ROAD_DAMAGE_CONF_THRESHOLD
        t0 = time.perf_counter()

        results = self.model.predict(
            source=frame,
            conf=conf,
            iou=0.40,
            device=self.device,
            imgsz=settings.INFERENCE_IMAGE_SIZE,
            verbose=False
        )

        latency_ms = (time.perf_counter() - t0) * 1000.0
        raw_detections: List[Dict[str, Any]] = []

        if not results or len(results) == 0:
            return raw_detections, latency_ms

        result = results[0]
        h, w = frame.shape[:2]

        for box in result.boxes:
            cls_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())
            class_name = self.DAMAGE_CLASSES.get(cls_id, result.names.get(cls_id, f"damage_{cls_id}"))

            xyxy = box.xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = [int(val) for val in xyxy]

            # 1. Edge & Border & Timestamp Artifact Rejection:
            # Skip boxes in top margin (where camera OSD timestamp is drawn) or bottom margin (CP PLUS watermark)
            if x1 <= 10 or y1 <= 28 or x2 >= w - 10 or y2 >= h - 22:
                continue

            # 2. Maximum Area Filter:
            # Skip detections covering > 35% of the entire viewport (wall/table shadow false alarms)
            box_area = (x2 - x1) * (y2 - y1)
            if box_area > 0.35 * (w * h):
                continue

            # 3. Minimum Area Filter:
            # Skip tiny pixel noise dots (< 24x24 px)
            if (x2 - x1) < 24 or (y2 - y1) < 24:
                continue

            cx = ((x1 + x2) / 2.0) / w
            cy = ((y1 + y2) / 2.0) / h
            nw = (x2 - x1) / w
            nh = (y2 - y1) / h

            raw_detections.append({
                "category": "road_damage",
                "class_id": cls_id,
                "class_name": class_name,
                "confidence": round(confidence, 3),
                "bbox": [x1, y1, x2, y2],
                "normalized_bbox": [round(cx, 4), round(cy, 4), round(nw, 4), round(nh, 4)]
            })

        # 4. Strict Non-Maximum Suppression (IoU <= 0.18 & IoS <= 0.40) & Top-4 Cap
        raw_detections.sort(key=lambda d: d["confidence"], reverse=True)
        clean_detections: List[Dict[str, Any]] = []
        for cand in raw_detections:
            if not any(
                calculate_iou(cand["bbox"], acc["bbox"]) > 0.18 or
                calculate_ios(cand["bbox"], acc["bbox"]) > 0.40
                for acc in clean_detections
            ):
                clean_detections.append(cand)
            if len(clean_detections) >= 4:
                break

        return clean_detections, latency_ms


general_detector = GeneralObjectDetector()
road_damage_detector = RoadDamageDetector()
