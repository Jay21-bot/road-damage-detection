"""
AI Detection Control & Query API Endpoints
"""

from typing import Optional
from fastapi import APIRouter, Query, HTTPException, status, Depends

from app.core.config import settings
from app.core.security import verify_api_key
from app.schemas.detection import (
    DetectionControlResponse,
    DetectionStatusResponse,
    DetectionHistoryResponse,
    DetectionDetailResponse
)
from app.services.detection_service import detection_service
from app.services.dual_detector import dual_engine
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/detection", tags=["AI Detection Engine"])


@router.post("/start", response_model=DetectionControlResponse, dependencies=[Depends(verify_api_key)])
async def start_detection():
    """Starts or resumes real-time AI inference on the video stream."""
    detection_service.set_active(True)
    status = dual_engine.status
    await ws_manager.broadcast({
        "event": "DETECTION_STATE_CHANGED",
        "detection_active": True
    })
    return {
        "detection_active": True,
        "message": "AI Road Damage & Object Detection started.",
        "active_models": {
            "general_model": status["general_model_ready"],
            "road_damage_model": status["road_damage_model_ready"]
        }
    }


@router.post("/stop", response_model=DetectionControlResponse, dependencies=[Depends(verify_api_key)])
async def stop_detection():
    """Pauses AI inference while preserving raw video stream transmission."""
    detection_service.set_active(False)
    status = dual_engine.status
    await ws_manager.broadcast({
        "event": "DETECTION_STATE_CHANGED",
        "detection_active": False
    })
    return {
        "detection_active": False,
        "message": "AI Detection paused.",
        "active_models": {
            "general_model": status["general_model_ready"],
            "road_damage_model": status["road_damage_model_ready"]
        }
    }


@router.get("/status", response_model=DetectionStatusResponse)
async def get_detection_status():
    """Returns AI model readiness, device information, and running inference counters."""
    engine_status = dual_engine.status
    stats = detection_service.get_statistics()
    return {
        "detection_active": detection_service.is_active,
        "general_model_ready": engine_status["general_model_ready"],
        "road_damage_model_ready": engine_status["road_damage_model_ready"],
        "device": engine_status.get("device", "cpu"),
        "frame_skip": engine_status.get("frame_skip", settings.FRAME_SKIP),
        "avg_latency_ms": engine_status.get("avg_latency_ms", 0.0),
        "total_inferences": engine_status["total_inferences"],
        "total_damages_detected": stats["total_road_damages"],
        "total_objects_detected": stats["total_objects"]
    }


@router.get("s", response_model=DetectionHistoryResponse)
@router.get("/", response_model=DetectionHistoryResponse)
async def get_detections(
    category: Optional[str] = Query(None, description="Filter by 'road_damage' or 'general_object'"),
    class_name: Optional[str] = Query(None, description="Filter by class name (e.g. 'pothole', 'car')"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page")
):
    """
    Search and filter historical detection records with pagination from database.
    Supports filtering by damage/object category and minimum confidence.
    """
    return await detection_service.get_detections(
        category=category,
        class_name=class_name,
        min_confidence=min_confidence,
        page=page,
        page_size=page_size
    )


@router.get("s/{detection_id}", response_model=DetectionDetailResponse)
@router.get("/{detection_id}", response_model=DetectionDetailResponse)
async def get_detection_detail(detection_id: str):
    """Retrieves full incident report, bounding box coordinates, and snapshot URL."""
    detail = await detection_service.get_detection_by_id(detection_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detection event with ID '{detection_id}' not found."
        )
    return detail
