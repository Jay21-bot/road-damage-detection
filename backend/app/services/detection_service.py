"""
Runtime Detection Coordinator & State Service
Manages real-time AI processing toggle, streaming frame generator,
in-memory detection history, and asynchronous database persistence (SQLite/PostgreSQL).
"""

import time
import uuid
import queue
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional, Generator
import cv2
import numpy as np
import psutil
from sqlalchemy import select, func, desc

from app.core.config import settings
from app.core.logging import logger
from app.db.models import Camera, DetectionSession, DetectionEvent, BoundingBox
from app.db.session import get_sync_session, AsyncSessionLocal
from app.services.camera_stream import camera_manager, CameraState
from app.services.video_pipeline import video_pipeline
from app.services.dual_detector import dual_engine
from app.services.snapshot_service import snapshot_service


class DetectionService:
    """Coordinates runtime detection loop, history buffer, snapshots, and database persistence."""

    def __init__(self, max_history: int = 500):
        self._is_active = True  # Detection active by default
        self._lock = threading.Lock()
        self._max_history = max_history
        self._history: List[Dict[str, Any]] = []
        self._start_time = time.time()
        self._last_snapshot_time = 0.0  # Snapshot rate limiter to prevent disk I/O bottlenecks
        self._total_damages = 0
        self._total_objects = 0
        self._damage_breakdown: Dict[str, int] = {
            "pothole": 0,
            "longitudinal_crack": 0,
            "transverse_crack": 0,
            "alligator_crack": 0
        }
        self._object_breakdown: Dict[str, int] = {
            "car": 0,
            "truck": 0,
            "bus": 0,
            "motorcycle": 0,
            "pedestrian": 0,
            "bicycle": 0,
            "traffic light": 0
        }

        # Database session and persistence queue
        self.camera_db_id = "cam_cp_e25a_01"
        self.current_session_id = str(uuid.uuid4())
        self._db_queue = queue.Queue(maxsize=2000)
        self._db_worker_running = True
        self._db_worker_thread = threading.Thread(
            target=self._db_persistence_worker,
            name="DbPersistenceWorker",
            daemon=True
        )
        self._db_worker_thread.start()
        logger.info(f"Database persistence worker thread started for session {self.current_session_id[:8]}...")

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._is_active

    def set_active(self, active: bool):
        with self._lock:
            self._is_active = active
        logger.info(f"AI Detection state toggled: {'ENABLED' if active else 'DISABLED'}")

    def record_detections(self, detections: List[Dict[str, Any]], frame: Optional[np.ndarray] = None):
        """
        Thread-safely stores detection items, triggers snapshot persistence,
        and pushes records to the non-blocking background database queue.
        """
        if not detections:
            return

        with self._lock:
            for d in detections:
                cat = d.get("category", "")
                cls_name = d.get("class_name", "").lower()
                conf = d.get("confidence", 0.0)
                bbox = d.get("bbox", [])
                det_id = d.get("id") or str(uuid.uuid4())
                d["id"] = det_id

                # Rate-limit incident snapshots (max 1 snapshot per 2.0s) to prevent disk I/O bottlenecks
                now = time.time()
                if frame is not None and (now - self._last_snapshot_time >= 2.0) and (cat == "road_damage" or conf >= 0.75):
                    if not d.get("snapshot_path"):
                        self._last_snapshot_time = now
                        snap_url = snapshot_service.save_detection_snapshot(
                            frame=frame,
                            event_id=det_id,
                            category=cat,
                            class_name=cls_name,
                            confidence=conf,
                            bbox=bbox,
                            crop=False
                        )
                        d["snapshot_path"] = snap_url

                self._history.insert(0, d)

                if cat == "road_damage":
                    self._total_damages += 1
                    self._damage_breakdown[cls_name] = self._damage_breakdown.get(cls_name, 0) + 1
                else:
                    self._total_objects += 1
                    self._object_breakdown[cls_name] = self._object_breakdown.get(cls_name, 0) + 1

                # Push copy to background DB worker queue without blocking
                try:
                    self._db_queue.put_nowait(dict(d))
                except queue.Full:
                    pass

            # Trim in-memory history to avoid memory growth
            if len(self._history) > self._max_history:
                self._history = self._history[: self._max_history]

    def _db_persistence_worker(self):
        """Background thread consuming detection items and committing them into database."""
        while self._db_worker_running:
            batch = []
            try:
                # Wait for first item
                item = self._db_queue.get(timeout=0.5)
                batch.append(item)
                # Drain available items up to batch size 25
                while len(batch) < 25 and not self._db_queue.empty():
                    batch.append(self._db_queue.get_nowait())
            except queue.Empty:
                continue
            except Exception as e:
                logger.debug(f"DB queue read exception: {e}")
                continue

            if not batch:
                continue

            # Persist batch to DB using synchronous session
            try:
                with get_sync_session() as session:
                    # 1. Ensure Camera record exists
                    camera_rec = session.get(Camera, self.camera_db_id)
                    if not camera_rec:
                        camera_rec = Camera(
                            id=self.camera_db_id,
                            name=settings.CAMERA_NAME,
                            ip_address=settings.CAMERA_IP,
                            rtsp_port=settings.CAMERA_RTSP_PORT,
                            onvif_port=settings.CAMERA_ONVIF_PORT,
                            stream_path="/cam/realmonitor?channel=1&subtype=0",
                            is_active=True,
                            last_seen=datetime.utcnow()
                        )
                        session.add(camera_rec)
                        session.flush()

                    # 2. Ensure DetectionSession record exists
                    session_rec = session.get(DetectionSession, self.current_session_id)
                    if not session_rec:
                        session_rec = DetectionSession(
                            id=self.current_session_id,
                            camera_id=self.camera_db_id,
                            started_at=datetime.utcnow(),
                            total_frames_processed=0
                        )
                        session.add(session_rec)
                        session.flush()

                    # 3. Create DetectionEvents and BoundingBoxes
                    for d in batch:
                        # Skip if event ID already exists in DB to prevent duplicate key errors
                        if session.get(DetectionEvent, d["id"]):
                            continue

                        epoch = d.get("timestamp", time.time())
                        det_event = DetectionEvent(
                            id=d["id"],
                            session_id=self.current_session_id,
                            timestamp=datetime.utcfromtimestamp(epoch),
                            epoch_time=epoch,
                            category=d.get("category", "general_object"),
                            primary_class=d.get("class_name", "unknown"),
                            confidence=float(d.get("confidence", 0.0)),
                            snapshot_path=d.get("snapshot_path"),
                            flagged_for_review=d.get("flagged_for_review", False)
                        )
                        session.add(det_event)

                        # Add BoundingBox child record
                        bbox = d.get("bbox", [0, 0, 0, 0])
                        norm_box = d.get("normalized_bbox", [0.0, 0.0, 0.0, 0.0])
                        box_rec = BoundingBox(
                            id=str(uuid.uuid4()),
                            event_id=d["id"],
                            class_name=d.get("class_name", "unknown"),
                            confidence=float(d.get("confidence", 0.0)),
                            x_min=float(bbox[0]) if len(bbox) > 0 else 0.0,
                            y_min=float(bbox[1]) if len(bbox) > 1 else 0.0,
                            x_max=float(bbox[2]) if len(bbox) > 2 else 0.0,
                            y_max=float(bbox[3]) if len(bbox) > 3 else 0.0,
                            normalized_cx=float(norm_box[0]) if len(norm_box) > 0 else 0.0,
                            normalized_cy=float(norm_box[1]) if len(norm_box) > 1 else 0.0,
                            normalized_w=float(norm_box[2]) if len(norm_box) > 2 else 0.0,
                            normalized_h=float(norm_box[3]) if len(norm_box) > 3 else 0.0,
                        )
                        session.add(box_rec)

                    session_rec.total_frames_processed += len(batch)
                    session.commit()
            except Exception as e:
                logger.warning(f"Database batch insert error: {e}")

    async def get_detections(
        self,
        category: Optional[str] = None,
        class_name: Optional[str] = None,
        min_confidence: float = 0.0,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        Queries detection records with filtering and pagination.
        Attempts database retrieval; falls back cleanly to in-memory cache if DB is empty.
        """
        try:
            async with AsyncSessionLocal() as session:
                query = select(DetectionEvent)
                count_query = select(func.count(DetectionEvent.id))

                if category:
                    query = query.where(DetectionEvent.category == category)
                    count_query = count_query.where(DetectionEvent.category == category)
                if class_name:
                    query = query.where(func.lower(DetectionEvent.primary_class) == class_name.lower())
                    count_query = count_query.where(func.lower(DetectionEvent.primary_class) == class_name.lower())
                if min_confidence > 0.0:
                    query = query.where(DetectionEvent.confidence >= min_confidence)
                    count_query = count_query.where(DetectionEvent.confidence >= min_confidence)

                # Execute count query
                total_res = await session.execute(count_query)
                total_records = total_res.scalar() or 0

                if total_records > 0:
                    # Execute paginated events query with bounding boxes
                    query = query.order_by(desc(DetectionEvent.epoch_time))
                    query = query.offset((page - 1) * page_size).limit(page_size)
                    results = await session.execute(query)
                    events = results.scalars().all()

                    formatted_items = []
                    for ev in events:
                        # Load associated bounding box for coordinates
                        box_stmt = select(BoundingBox).where(BoundingBox.event_id == ev.id)
                        box_res = await session.execute(box_stmt)
                        box = box_res.scalars().first()

                        bbox = [int(box.x_min), int(box.y_min), int(box.x_max), int(box.y_max)] if box else [0, 0, 0, 0]
                        norm_box = [box.normalized_cx, box.normalized_cy, box.normalized_w, box.normalized_h] if box else [0.0, 0.0, 0.0, 0.0]

                        formatted_items.append({
                            "id": ev.id,
                            "timestamp": ev.epoch_time,
                            "category": ev.category,
                            "class_id": 0,
                            "class_name": ev.primary_class,
                            "confidence": ev.confidence,
                            "bbox": bbox,
                            "normalized_bbox": norm_box,
                            "snapshot_path": ev.snapshot_path,
                            "flagged_for_review": ev.flagged_for_review
                        })

                    return {
                        "total_records": total_records,
                        "page": page,
                        "page_size": page_size,
                        "detections": formatted_items
                    }
        except Exception as e:
            logger.debug(f"DB query fallback to in-memory: {e}")

        # In-memory fallback
        with self._lock:
            filtered = self._history
            if category:
                filtered = [d for d in filtered if d.get("category") == category]
            if class_name:
                filtered = [d for d in filtered if d.get("class_name", "").lower() == class_name.lower()]
            if min_confidence > 0.0:
                filtered = [d for d in filtered if d.get("confidence", 0.0) >= min_confidence]

            total_records = len(filtered)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size

            return {
                "total_records": total_records,
                "page": page,
                "page_size": page_size,
                "detections": filtered[start_idx:end_idx]
            }

    async def get_detection_by_id(self, detection_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves comprehensive details for a single detection event including bounding boxes."""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(DetectionEvent).where(DetectionEvent.id == detection_id)
                res = await session.execute(stmt)
                ev = res.scalars().first()
                if ev:
                    box_stmt = select(BoundingBox).where(BoundingBox.event_id == ev.id)
                    box_res = await session.execute(box_stmt)
                    boxes = box_res.scalars().all()

                    return {
                        "id": ev.id,
                        "session_id": ev.session_id,
                        "timestamp": ev.epoch_time,
                        "iso_time": ev.timestamp.isoformat() if ev.timestamp else None,
                        "category": ev.category,
                        "class_name": ev.primary_class,
                        "confidence": ev.confidence,
                        "snapshot_path": ev.snapshot_path,
                        "flagged_for_review": ev.flagged_for_review,
                        "bounding_boxes": [b.to_dict() for b in boxes]
                    }
        except Exception as e:
            logger.debug(f"DB lookup fallback for detection {detection_id}: {e}")

        # In-memory fallback
        with self._lock:
            for d in self._history:
                if d.get("id") == detection_id:
                    bbox = d.get("bbox", [0, 0, 0, 0])
                    norm_box = d.get("normalized_bbox", [0.0, 0.0, 0.0, 0.0])
                    return {
                        "id": d["id"],
                        "session_id": self.current_session_id,
                        "timestamp": d.get("timestamp", time.time()),
                        "iso_time": datetime.utcnow().isoformat(),
                        "category": d.get("category", "general_object"),
                        "class_name": d.get("class_name", "unknown"),
                        "confidence": d.get("confidence", 0.0),
                        "snapshot_path": d.get("snapshot_path"),
                        "flagged_for_review": d.get("flagged_for_review", False),
                        "bounding_boxes": [{
                            "id": f"box_{d['id']}",
                            "class_name": d.get("class_name", "unknown"),
                            "confidence": d.get("confidence", 0.0),
                            "bbox": bbox,
                            "normalized_bbox": norm_box
                        }]
                    }
            return None

    def get_statistics(self) -> Dict[str, Any]:
        """Returns consolidated analytics for dashboard consumption."""
        with self._lock:
            status = dual_engine.status
            avg_fps = 1000.0 / status["avg_latency_ms"] if status["avg_latency_ms"] > 0 else 0.0
            return {
                "total_detections": self._total_damages + self._total_objects,
                "total_road_damages": self._total_damages,
                "total_objects": self._total_objects,
                "damage_by_class": dict(self._damage_breakdown),
                "objects_by_class": dict(self._object_breakdown),
                "avg_inference_fps": round(avg_fps, 1),
                "system_uptime_seconds": round(time.time() - self._start_time, 1)
            }

    def get_system_health(self) -> Dict[str, Any]:
        """Provides hardware and pipeline health telemetry."""
        proc = psutil.Process()
        mem_info = proc.memory_info()
        vm = psutil.virtual_memory()

        return {
            "status": "HEALTHY",
            "uptime_seconds": round(time.time() - self._start_time, 1),
            "cpu_usage_percent": psutil.cpu_percent(interval=None),
            "memory_usage_mb": round(mem_info.rss / (1024 * 1024), 1),
            "memory_percent": round(vm.percent, 1),
            "camera_connected": camera_manager.state in (CameraState.CONNECTED, CameraState.STREAMING),
            "ai_models_loaded": dual_engine.status["general_model_ready"] and dual_engine.status["road_damage_model_ready"],
            "detection_active": self._is_active
        }

    def generate_mjpeg_stream(self) -> Generator[bytes, None, None]:
        """
        Yields live multipart/x-mixed-replace JPEG frames.
        Executes AI inference when enabled, snapshots incidents, and annotates HUD.
        """
        while True:
            raw_frame = video_pipeline.frame_buffer.get(timeout=0.2)

            if raw_frame is None:
                # Fallback to simulated road stream if buffer is idle
                raw_frame = camera_manager.generate_synthetic_frame("STANDBY | AWAITING STREAM BUFFER")

            detections = []
            if self.is_active:
                detections, _ = dual_engine.process_frame(raw_frame)
                self.record_detections(detections, frame=raw_frame)

            # Annotate frame with HUD and bounding boxes
            annotated = video_pipeline.annotate_frame(
                raw_frame,
                detections=detections if self.is_active else []
            )

            # Compress to JPEG
            try:
                jpeg_bytes = video_pipeline.encode_jpeg(annotated, quality=65)
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + jpeg_bytes + b"\r\n"
                )
            except Exception as e:
                logger.error(f"JPEG encoding failed in MJPEG stream: {e}")
            time.sleep(0.02)


detection_service = DetectionService()
