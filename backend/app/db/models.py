"""
Database Models (SQLAlchemy ORM)
Defines relational schemas for cameras, detection sessions, events, bounding boxes, and snapshot records.
Supports SQLite (development/edge) and PostgreSQL (production/cloud) transparently.
"""

from datetime import datetime
from typing import List, Optional
import uuid

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Index
)
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column

Base = declarative_base()


class Camera(Base):
    """Registered IP Surveillance Camera (e.g. CP PLUS CP-E25A)."""
    __tablename__ = "cameras"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(128), nullable=False, default="CP-PLUS-CP-E25A")
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False)
    rtsp_port: Mapped[int] = mapped_column(Integer, default=554)
    onvif_port: Mapped[int] = mapped_column(Integer, default=8000)
    stream_path: Mapped[str] = mapped_column(String(256), default="/cam/realmonitor?channel=1&subtype=0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    sessions: Mapped[List["DetectionSession"]] = relationship("DetectionSession", back_populates="camera", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "ip_address": self.ip_address,
            "rtsp_port": self.rtsp_port,
            "onvif_port": self.onvif_port,
            "stream_path": self.stream_path,
            "is_active": self.is_active,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DetectionSession(Base):
    """A continuous detection and streaming session for a camera."""
    __tablename__ = "detection_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    camera_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("cameras.id", ondelete="SET NULL"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    stopped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total_frames_processed: Mapped[int] = mapped_column(Integer, default=0)
    average_fps: Mapped[float] = mapped_column(Float, default=0.0)

    # Relationships
    camera: Mapped[Optional["Camera"]] = relationship("Camera", back_populates="sessions")
    events: Mapped[List["DetectionEvent"]] = relationship("DetectionEvent", back_populates="session", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "total_frames_processed": self.total_frames_processed,
            "average_fps": round(self.average_fps, 2),
        }


class DetectionEvent(Base):
    """An incident or detection event captured by the dual YOLO inference engine."""
    __tablename__ = "detection_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("detection_sessions.id", ondelete="SET NULL"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    epoch_time: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(32), index=True)  # 'road_damage' or 'general_object'
    primary_class: Mapped[str] = mapped_column(String(64), index=True)  # 'pothole', 'car', etc.
    confidence: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    snapshot_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    flagged_for_review: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    session: Mapped[Optional["DetectionSession"]] = relationship("DetectionSession", back_populates="events")
    bounding_boxes: Mapped[List["BoundingBox"]] = relationship("BoundingBox", back_populates="event", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_category_class", "category", "primary_class"),
        Index("idx_timestamp_category", "timestamp", "category"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "timestamp": self.epoch_time,
            "iso_time": self.timestamp.isoformat() if self.timestamp else None,
            "category": self.category,
            "class_name": self.primary_class,
            "confidence": round(self.confidence, 4),
            "snapshot_path": self.snapshot_path,
            "flagged_for_review": self.flagged_for_review,
            "bounding_boxes": [b.to_dict() for b in self.bounding_boxes] if self.bounding_boxes else []
        }


class BoundingBox(Base):
    """Individual bounding box prediction linked to a DetectionEvent."""
    __tablename__ = "bounding_boxes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(String(64), ForeignKey("detection_events.id", ondelete="CASCADE"), index=True)
    class_name: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Pixel Coordinates [x1, y1, x2, y2]
    x_min: Mapped[float] = mapped_column(Float, default=0.0)
    y_min: Mapped[float] = mapped_column(Float, default=0.0)
    x_max: Mapped[float] = mapped_column(Float, default=0.0)
    y_max: Mapped[float] = mapped_column(Float, default=0.0)

    # Normalized Coordinates [cx, cy, nw, nh] (0.0 to 1.0)
    normalized_cx: Mapped[float] = mapped_column(Float, default=0.0)
    normalized_cy: Mapped[float] = mapped_column(Float, default=0.0)
    normalized_w: Mapped[float] = mapped_column(Float, default=0.0)
    normalized_h: Mapped[float] = mapped_column(Float, default=0.0)

    # Relationships
    event: Mapped["DetectionEvent"] = relationship("DetectionEvent", back_populates="bounding_boxes")

    def to_dict(self):
        return {
            "id": self.id,
            "class_name": self.class_name,
            "confidence": round(self.confidence, 4),
            "bbox": [int(self.x_min), int(self.y_min), int(self.x_max), int(self.y_max)],
            "normalized_bbox": [
                round(self.normalized_cx, 4),
                round(self.normalized_cy, 4),
                round(self.normalized_w, 4),
                round(self.normalized_h, 4)
            ]
        }
