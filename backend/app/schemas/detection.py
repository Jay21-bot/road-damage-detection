"""
Detection Pydantic Schemas
Defines request and response structures for AI detection control and query history.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DetectionItem(BaseModel):
    """Single bounding box detection record."""
    id: str
    timestamp: float
    category: str = Field(..., description="'road_damage' or 'general_object'")
    class_id: int = 0
    class_name: str
    confidence: float
    bbox: List[int] = Field(..., description="[x1, y1, x2, y2] pixel coordinates")
    normalized_bbox: List[float] = Field(..., description="[cx, cy, nw, nh] normalized coordinates")
    snapshot_path: Optional[str] = None
    flagged_for_review: Optional[bool] = False


class BoundingBoxItem(BaseModel):
    """Normalized & pixel coordinates for individual detected box."""
    id: str
    class_name: str
    confidence: float
    bbox: List[int]
    normalized_bbox: List[float]


class DetectionDetailResponse(BaseModel):
    """Comprehensive incident event report with bounding boxes & snapshot."""
    id: str
    session_id: Optional[str] = None
    timestamp: float
    iso_time: Optional[str] = None
    category: str
    class_name: str
    confidence: float
    snapshot_path: Optional[str] = None
    flagged_for_review: bool = False
    bounding_boxes: List[BoundingBoxItem] = []


class DetectionControlResponse(BaseModel):
    """Status confirmation for starting/stopping detection."""
    detection_active: bool
    message: str
    active_models: Dict[str, bool]


class DetectionStatusResponse(BaseModel):
    """Detailed telemetry on detection engines."""
    detection_active: bool
    general_model_ready: bool
    road_damage_model_ready: bool
    device: str
    frame_skip: int
    avg_latency_ms: float
    total_inferences: int
    total_damages_detected: int
    total_objects_detected: int


class DetectionHistoryResponse(BaseModel):
    """Paginated collection of past detections."""
    total_records: int
    page: int
    page_size: int
    detections: List[DetectionItem]
