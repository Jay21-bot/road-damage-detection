"""
Statistics & System Health Schemas
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel


class SystemHealthResponse(BaseModel):
    """Overall system and hardware health status."""
    status: str
    uptime_seconds: float
    cpu_usage_percent: float
    memory_usage_mb: float
    memory_percent: float
    camera_connected: bool
    ai_models_loaded: bool
    detection_active: bool


class StatisticsResponse(BaseModel):
    """Aggregated traffic and road damage metrics for dashboard visualization."""
    total_detections: int
    total_road_damages: int
    total_objects: int
    damage_by_class: Dict[str, int]
    objects_by_class: Dict[str, int]
    avg_inference_fps: float
    system_uptime_seconds: float
