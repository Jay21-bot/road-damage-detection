"""
Camera Management & Streaming API Endpoints
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.logging import logger
from app.core.security import verify_api_key
from app.schemas.camera import (
    CameraConnectRequest,
    CameraStatusResponse,
    CameraActionResponse
)
from app.services.camera_stream import camera_manager
from app.services.detection_service import detection_service
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/camera", tags=["Camera Management"])


@router.get("/status", response_model=CameraStatusResponse)
async def get_camera_status():
    """Returns the real-time operational status and diagnostics of the CP PLUS camera."""
    return camera_manager.stream_info


@router.post("/connect", response_model=CameraActionResponse, dependencies=[Depends(verify_api_key)])
async def connect_camera(request: CameraConnectRequest):
    """
    Dynamically connects or updates the CP PLUS camera connection parameters.
    Allows changing IP address, credentials, or custom RTSP URLs on the fly.
    """
    if request.ip_address:
        settings.CAMERA_IP = request.ip_address
    if request.rtsp_port:
        settings.CAMERA_RTSP_PORT = request.rtsp_port
    if request.onvif_port:
        settings.CAMERA_ONVIF_PORT = request.onvif_port
    if request.username:
        settings.CAMERA_USERNAME = request.username
    if request.password:
        settings.CAMERA_PASSWORD = request.password
    if request.stream_subtype is not None:
        settings.CAMERA_STREAM_SUBTYPE = request.stream_subtype
    if request.rtsp_override_url is not None:
        settings.CAMERA_RTSP_OVERRIDE_URL = request.rtsp_override_url

    # Disconnect if previously connected to re-negotiate new stream profile
    camera_manager.disconnect()
    success = camera_manager.connect()

    # Broadcast updated camera state to all active WebSocket clients
    await ws_manager.broadcast({
        "event": "CAMERA_STATUS_CHANGED",
        "camera": camera_manager.stream_info
    })

    return {
        "success": success,
        "message": "Connected to camera stream successfully." if success else f"Failed to connect: {camera_manager.last_error}",
        "camera_status": camera_manager.stream_info
    }


@router.post("/disconnect", response_model=CameraActionResponse, dependencies=[Depends(verify_api_key)])
async def disconnect_camera():
    """Halts video ingestion and closes camera socket cleanly."""
    camera_manager.disconnect()
    await ws_manager.broadcast({
        "event": "CAMERA_STATUS_CHANGED",
        "camera": camera_manager.stream_info
    })
    return {
        "success": True,
        "message": "Camera disconnected successfully.",
        "camera_status": camera_manager.stream_info
    }


@router.post("/mode/demo")
async def switch_camera_to_demo():
    """Switches stream to loop bundled road damage footage."""
    camera_manager.switch_to_demo()
    await ws_manager.broadcast({
        "event": "CAMERA_STATUS_CHANGED",
        "camera": camera_manager.stream_info
    })
    return {"success": True, "mode": "demo", "camera_status": camera_manager.stream_info}


@router.post("/mode/live")
async def switch_camera_to_live():
    """Switches stream to real CP PLUS physical camera."""
    success = camera_manager.switch_to_live()
    await ws_manager.broadcast({
        "event": "CAMERA_STATUS_CHANGED",
        "camera": camera_manager.stream_info
    })
    return {"success": success, "mode": "live" if success else "demo_fallback", "camera_status": camera_manager.stream_info}


@router.get("/stream")
async def get_camera_stream():
    """
    Live MJPEG Annotated Video Stream.
    Directly embeddable in standard HTML `<img src="/api/v1/camera/stream" />` elements.
    Streams video with overlaid HUD bounding boxes and classification tags.
    """
    return StreamingResponse(
        detection_service.generate_mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
