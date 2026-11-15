"""
Camera Pydantic Schemas
Defines request and response validation models for camera connection and diagnostics.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class CameraConnectRequest(BaseModel):
    """Payload to initiate connection to CP PLUS CP-E25A camera."""
    ip_address: Optional[str] = Field(None, description="Camera IP address")
    rtsp_port: Optional[int] = Field(554, description="RTSP port (default: 554)")
    onvif_port: Optional[int] = Field(8000, description="ONVIF port (default: 8000)")
    username: Optional[str] = Field(None, description="Camera username")
    password: Optional[str] = Field(None, description="Camera password")
    stream_subtype: Optional[int] = Field(0, description="0: Main stream (1080p), 1: Sub-stream (360p)")
    rtsp_override_url: Optional[str] = Field(None, description="Custom RTSP URL override")


class CameraStatusResponse(BaseModel):
    """Current state and diagnostics of the camera stream."""
    state: str
    active_url: Optional[str] = None
    resolution: str
    fps: float
    frames_received: int
    reconnect_attempts: int
    last_error: Optional[str] = None
    last_frame_age_seconds: Optional[float] = None


class CameraActionResponse(BaseModel):
    """Standard operation response."""
    success: bool
    message: str
    camera_status: CameraStatusResponse
