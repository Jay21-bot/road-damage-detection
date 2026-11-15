"""
Analytics & System Health Endpoints
"""

from fastapi import APIRouter
from app.schemas.stats import SystemHealthResponse, StatisticsResponse
from app.services.detection_service import detection_service

router = APIRouter(tags=["Analytics & Health"])


@router.get("/health", response_model=SystemHealthResponse)
async def get_health():
    """Returns overall server, memory, camera, and model health."""
    return detection_service.get_system_health()


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics():
    """Returns aggregated traffic and road damage breakdown metrics."""
    return detection_service.get_statistics()
