"""
Real-Time OpenCV Video Processing Pipeline
Provides thread-safe zero-latency frame buffering, resolution letterboxing,
surveillance HUD annotation, and low-latency JPEG stream compression.
"""

import time
import queue
import threading
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.services.camera_stream import camera_manager, CameraState


class ZeroLatencyFrameBuffer:
    """
    A thread-safe single-slot ring buffer.
    Always provides the newest frame to the AI inference worker,
    instantly discarding stale frames to eliminate network delay drift.
    """

    def __init__(self, maxsize: int = 1):
        self._queue = queue.Queue(maxsize=maxsize)
        self._dropped_frames = 0
        self._lock = threading.Lock()

    def put(self, frame: np.ndarray):
        """Pushes the newest frame, discarding existing frame if full."""
        try:
            self._queue.put_nowait(frame)
        except queue.Full:
            try:
                # Discard stale frame
                _ = self._queue.get_nowait()
                with self._lock:
                    self._dropped_frames += 1
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(frame)
            except queue.Full:
                pass

    def get(self, timeout: float = 0.5) -> Optional[np.ndarray]:
        """Retrieves the newest available frame."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @property
    def dropped_frames(self) -> int:
        with self._lock:
            return self._dropped_frames


class VideoPipeline:
    """
    Multi-threaded video processing pipeline for real-time frame ingestion,
    preprocessing, HUD annotation, and streaming.
    """

    # Palette definitions (BGR for OpenCV)
    COLOR_ROAD_DAMAGE = (45, 50, 240)     # Neon Red / Crimson
    COLOR_GENERAL_OBJECT = (240, 180, 20)  # Neon Cyan / Electric Blue
    COLOR_HUD_BG = (20, 20, 20)           # Deep Dark Gray
    COLOR_HUD_TEXT = (240, 240, 240)      # Crisp White
    COLOR_ACCENT = (0, 230, 115)          # Emerald Green

    def __init__(self):
        self.frame_buffer = ZeroLatencyFrameBuffer(maxsize=1)
        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._fps_counter = 0
        self._current_fps = 0.0
        self._last_fps_calc_time = time.time()
        self._processed_frames = 0
        self._lock = threading.Lock()

    @property
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "pipeline_running": self._is_running,
                "current_fps": round(self._current_fps, 2),
                "total_processed": self._processed_frames,
                "dropped_stale_frames": self.frame_buffer.dropped_frames
            }

    @staticmethod
    def letterbox(image: np.ndarray, target_size: int = 640) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        """
        Resizes and pads image to square target size for YOLO inference,
        preserving original aspect ratio.
        Returns: (padded_image, scale_ratio, (pad_left, pad_top))
        """
        h, w = image.shape[:2]
        scale = min(target_size / h, target_size / w)
        new_w, new_h = int(w * scale), int(h * scale)

        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Create square canvas
        canvas = np.full((target_size, target_size, 3), 114, dtype=np.uint8)
        pad_x = (target_size - new_w) // 2
        pad_y = (target_size - new_h) // 2
        canvas[pad_y : pad_y + new_h, pad_x : pad_x + new_w] = resized

        return canvas, scale, (pad_x, pad_y)

    def annotate_frame(
        self,
        frame: np.ndarray,
        detections: Optional[List[Dict[str, Any]]] = None,
        custom_fps: Optional[float] = None
    ) -> np.ndarray:
        """
        Draws high-visibility bounding boxes, category tags, corner accents,
        and an executive surveillance HUD banner onto the video frame.
        """
        annotated = frame.copy()
        h, w = annotated.shape[:2]
        detections = detections or []

        # 1. Render Detections
        damage_count = 0
        object_count = 0

        for det in detections:
            bbox = det.get("bbox", [0, 0, 0, 0])
            x1, y1, x2, y2 = [int(v) for v in bbox]
            category = det.get("category", "general_object")
            class_name = det.get("class_name", "object")
            conf = det.get("confidence", 0.0)

            # Determine styling by category
            if category == "road_damage":
                color = self.COLOR_ROAD_DAMAGE
                damage_count += 1
                tag_prefix = "[DMG]"
            else:
                color = self.COLOR_GENERAL_OBJECT
                object_count += 1
                tag_prefix = "[OBJ]"

            # Draw clean, sleek bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Label badge
            label_text = f"{tag_prefix} {class_name.upper()} {conf:.0%}"
            font_scale = 0.38 if w <= 640 else 0.45
            (text_w, text_h), baseline = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)

            badge_y1 = max(0, y1 - text_h - 6)
            badge_y2 = y1
            cv2.rectangle(annotated, (x1, badge_y1), (x1 + text_w + 6, badge_y2), color, -1)
            cv2.putText(
                annotated,
                label_text,
                (x1 + 3, badge_y2 - 3),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale,
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )

        # 2. Render Executive Surveillance HUD Banner
        if isinstance(custom_fps, dict):
            fps_val = custom_fps.get("fps")
            if fps_val is None and "latency_ms" in custom_fps and custom_fps["latency_ms"] > 0:
                fps_val = 1000.0 / custom_fps["latency_ms"]
            fps_to_show = float(fps_val) if fps_val is not None else self._current_fps
        elif custom_fps is not None:
            fps_to_show = float(custom_fps)
        else:
            fps_to_show = self._current_fps

        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")

        # Top banner overlay (semi-transparent dark)
        banner_h = 30 if h <= 480 else 40
        overlay = annotated.copy()
        cv2.rectangle(overlay, (0, 0), (w, banner_h), self.COLOR_HUD_BG, -1)
        cv2.addWeighted(overlay, 0.75, annotated, 0.25, 0, annotated)

        # Responsive HUD spacing
        y_text = 20 if h <= 480 else 26
        hud_font_scale = 0.36 if w <= 640 else 0.48

        cam_text = "CAM: CP-E25A [DEMO]" if camera_manager.is_demo else "CAM: CP-E25A [LIVE]"
        cv2.putText(annotated, cam_text, (10, y_text), cv2.FONT_HERSHEY_SIMPLEX, hud_font_scale, self.COLOR_ACCENT, 1, cv2.LINE_AA)
        cv2.putText(annotated, f"TIME: {timestamp_str}", (int(w * 0.26), y_text), cv2.FONT_HERSHEY_SIMPLEX, hud_font_scale, self.COLOR_HUD_TEXT, 1, cv2.LINE_AA)
        cv2.putText(annotated, f"FPS: {fps_to_show:.1f}", (int(w * 0.60), y_text), cv2.FONT_HERSHEY_SIMPLEX, hud_font_scale, (0, 220, 255), 1, cv2.LINE_AA)
        cv2.putText(annotated, f"DMG:{damage_count} OBJ:{object_count}", (int(w * 0.76), y_text), cv2.FONT_HERSHEY_SIMPLEX, hud_font_scale, self.COLOR_HUD_TEXT, 1, cv2.LINE_AA)

        # Subtle tactical corner reticle
        cv2.drawMarker(annotated, (w // 2, h // 2), (100, 100, 100), cv2.MARKER_CROSS, 20, 1)

        return annotated

    @staticmethod
    def encode_jpeg(frame: np.ndarray, quality: int = 65) -> bytes:
        """Compresses OpenCV frame into JPEG byte stream for MJPEG / WebSocket transfer."""
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), max(30, min(100, quality))]
        success, buffer = cv2.imencode(".jpg", frame, encode_params)
        if not success:
            raise ValueError("Failed to encode frame to JPEG format.")
        return buffer.tobytes()

    def start(self):
        """Starts background ingestion buffer thread."""
        with self._lock:
            if self._is_running:
                return
            self._is_running = True
            self._stop_event.clear()

        self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="VideoPipelineWorker")
        self._thread.start()
        logger.info("Video processing pipeline started.")

    def stop(self):
        """Stops background buffer worker."""
        with self._lock:
            if not self._is_running:
                return
            self._is_running = False
            self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Video processing pipeline stopped.")

    def _worker_loop(self):
        """Continuously pulls frames from CameraManager and populates ZeroLatencyFrameBuffer."""
        frame_interval = 1.0 / 30.0  # Target 30 FPS ingestion cap

        while not self._stop_event.is_set():
            loop_start = time.time()

            # Attempt to pull from physical camera or fallback to synthetic stream
            if camera_manager.state == CameraState.STREAMING:
                success, frame = camera_manager.get_latest_frame()
            else:
                # Fallback to synthetic road stream if camera is disconnected
                success = True
                frame = camera_manager.generate_synthetic_frame()

            if success and frame is not None:
                self.frame_buffer.put(frame)
                with self._lock:
                    self._processed_frames += 1
                    self._fps_counter += 1

                    # Recalculate rolling FPS every 1.0s
                    now = time.time()
                    elapsed = now - self._last_fps_calc_time
                    if elapsed >= 1.0:
                        self._current_fps = self._fps_counter / elapsed
                        self._fps_counter = 0
                        self._last_fps_calc_time = now

            # Sleep to match frame timing
            sleep_time = frame_interval - (time.time() - loop_start)
            if sleep_time > 0.002:
                time.sleep(sleep_time)


video_pipeline = VideoPipeline()
