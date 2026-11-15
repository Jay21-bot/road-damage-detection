"""
Snapshot Storage & Incident Image Service
Thread-safe image persistence for high-confidence road damage and object detections.
Handles JPEG encoding, bounding box cropping/annotation, and disk quota pruning.
"""

import os
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
import cv2
import numpy as np

from app.core.config import settings
from app.core.logging import logger


class SnapshotService:
    """Manages disk persistence and web URL resolution for detection incident snapshots."""

    def __init__(self):
        self.storage_dir = Path(__file__).resolve().parent.parent.parent / "storage" / "snapshots"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.max_snapshots = 2000  # Retain last 2,000 incident snapshots
        self.jpeg_quality = 88

    def save_detection_snapshot(
        self,
        frame: np.ndarray,
        event_id: str,
        category: str,
        class_name: str,
        confidence: float,
        bbox: Optional[List[int]] = None,
        crop: bool = False
    ) -> Optional[str]:
        """
        Saves a JPEG snapshot of the detected road damage or traffic object.
        Returns the relative web URL path (e.g., '/snapshots/snap_1700000000_abc12345_pothole.jpg').
        """
        if frame is None or frame.size == 0:
            return None

        try:
            timestamp_sec = int(time.time())
            safe_cls = class_name.lower().replace(" ", "_")
            short_id = event_id[:8] if event_id else "evt"
            filename = f"snap_{timestamp_sec}_{short_id}_{category}_{safe_cls}.jpg"
            file_path = self.storage_dir / filename

            # Make a copy so we don't modify the source video frame
            target_image = frame.copy()

            if crop and bbox and len(bbox) == 4:
                # Add margin to bounding box crop
                h, w = target_image.shape[:2]
                x1, y1, x2, y2 = bbox
                pad_x = int((x2 - x1) * 0.2)
                pad_y = int((y2 - y1) * 0.2)
                cx1 = max(0, x1 - pad_x)
                cy1 = max(0, y1 - pad_y)
                cx2 = min(w, x2 + pad_x)
                cy2 = min(h, y2 + pad_y)
                if cx2 > cx1 and cy2 > cy1:
                    target_image = target_image[cy1:cy2, cx1:cx2]
            elif bbox and len(bbox) == 4:
                # Overlay focused HUD indicator around target on full frame
                x1, y1, x2, y2 = bbox
                color = (40, 42, 255) if category == "road_damage" else (255, 229, 0)
                cv2.rectangle(target_image, (x1, y1), (x2, y2), color, 2)
                label = f"{class_name.upper()} {confidence * 100:.0f}%"
                cv2.putText(target_image, label, (x1, max(20, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            # Write compressed JPEG to disk
            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
            success = cv2.imwrite(str(file_path), target_image, encode_params)

            if success:
                logger.debug(f"Saved incident snapshot to {file_path.name}")
                return f"/snapshots/{filename}"
            else:
                logger.warning(f"cv2.imwrite failed for snapshot: {file_path}")
                return None
        except Exception as e:
            logger.error(f"Error saving detection snapshot: {e}")
            return None

    def prune_old_snapshots(self):
        """Prunes oldest snapshots if storage directory exceeds maximum quota."""
        try:
            files = sorted(
                self.storage_dir.glob("snap_*.jpg"),
                key=lambda f: f.stat().st_mtime
            )
            if len(files) > self.max_snapshots:
                excess = len(files) - self.max_snapshots
                for f in files[:excess]:
                    try:
                        f.unlink()
                    except Exception:
                        pass
                logger.info(f"Pruned {excess} expired snapshots from disk storage.")
        except Exception as e:
            logger.warning(f"Error during snapshot pruning: {e}")


snapshot_service = SnapshotService()
