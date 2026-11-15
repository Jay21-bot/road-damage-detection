"""
Application Configuration Module
Handles environment variable loading, validation, and CP PLUS camera stream construction.
"""

from typing import List, Optional
import os
from pathlib import Path
import re

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import Field, model_validator
except ImportError:
    from pydantic import BaseModel as BaseSettings, Field
    SettingsConfigDict = dict
    model_validator = None


class Settings(BaseSettings):
    """System-wide configuration settings loaded from environment or .env file."""

    # Application & Server
    PROJECT_NAME: str = "AI Road Damage & Object Detection System"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 7860
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: Optional[str] = None
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:7860",
        "http://localhost:8000",
        "https://*.bolt.new",
        "https://*.hf.space",
        "https://*.onrender.com",
        "https://*.railway.app",
        "https://huggingface.co"
    ]

    # Cloud Demo Mode (Streams real dual-YOLO inference over bundled road footage)
    DEMO_MODE: bool = False

    # Camera Configuration (CP PLUS CP-E25A / ONVIF / RTSP)
    CAMERA_NAME: str = "CP-PLUS-CP-E25A"
    CAMERA_IP: str = "192.168.1.100"
    CAMERA_RTSP_PORT: int = 5543
    CAMERA_RTSP_PATH: str = "/live/channel1"
    CAMERA_ONVIF_PORT: int = 8000
    CAMERA_USERNAME: str = "admin"
    CAMERA_PASSWORD: str = ""
    CAMERA_STREAM_SUBTYPE: int = 1  # 0: Main stream (high-res), 1: Sub-stream (low-res)
    CAMERA_RTSP_OVERRIDE_URL: Optional[str] = None
    CAMERA_RECONNECT_INTERVAL_SECONDS: int = 5
    CAMERA_MAX_RECONNECT_ATTEMPTS: int = 10

    # AI Model Inference Settings
    DEVICE: str = "cpu"  # Free cloud containers run on CPU
    ROAD_DAMAGE_MODEL_PATH: str = "models/road_damage_best.pt"
    GENERAL_OBJECT_MODEL_PATH: str = "models/yolov8n.pt"
    ROAD_DAMAGE_CONF_THRESHOLD: float = 0.35
    GENERAL_OBJECT_CONF_THRESHOLD: float = 0.45
    INFERENCE_IMAGE_SIZE: int = 640
    FRAME_SKIP: int = 2

    # Storage & Persistence
    DATABASE_URL: str = "sqlite+aiosqlite:///./road_detection.db"
    SNAPSHOT_DIR: str = "storage/snapshots"
    SAVE_DETECTION_SNAPSHOTS: bool = True

    # Security
    API_SECRET_KEY: str = "insecure_default_secret_change_in_production"

    model_config = SettingsConfigDict(
        env_file=[".env", str(Path(__file__).resolve().parent.parent.parent.parent / ".env")],
        env_file_encoding="utf-8",
        extra="ignore"
    )

    if model_validator:
        @model_validator(mode="after")
        def validate_production_settings(self):
            if self.APP_ENV.lower() == "production":
                if (
                    not self.API_SECRET_KEY
                    or "insecure" in self.API_SECRET_KEY.lower()
                    or "change_in_production" in self.API_SECRET_KEY.lower()
                    or len(self.API_SECRET_KEY) < 16
                ):
                    raise ValueError(
                        "In production mode (APP_ENV=production), API_SECRET_KEY must be securely configured "
                        "with at least 16 characters. Refusing startup with insecure secret."
                    )
            return self

    def get_cors_origins(self) -> List[str]:
        """Returns allowed CORS origins parsed from ALLOWED_ORIGINS or default list."""
        if self.ALLOWED_ORIGINS and self.ALLOWED_ORIGINS.strip():
            return [orig.strip() for orig in self.ALLOWED_ORIGINS.split(",") if orig.strip()]
        return self.CORS_ORIGINS

    def get_rtsp_url(self, mask_password: bool = False) -> str:
        """
        Constructs the standard RTSP URL for the camera.
        If CAMERA_RTSP_OVERRIDE_URL is provided, it is returned (with credentials masked if requested).
        """
        if self.CAMERA_RTSP_OVERRIDE_URL and self.CAMERA_RTSP_OVERRIDE_URL.strip():
            url = self.CAMERA_RTSP_OVERRIDE_URL
            if mask_password and "@" in url:
                try:
                    scheme, rest = url.split("://", 1)
                    user_pass, host_path = rest.split("@", 1)
                    if ":" in user_pass:
                        user, _ = user_pass.split(":", 1)
                        return f"{scheme}://{user}:********@{host_path}"
                    return f"{scheme}://********@{host_path}"
                except Exception:
                    return "rtsp://[MASKED_CREDENTIALS]@"
            return url

        pwd = "********" if mask_password else self.CAMERA_PASSWORD
        path = self.CAMERA_RTSP_PATH
        if not path.startswith("/"):
            path = "/" + path
        return (
            f"rtsp://{self.CAMERA_USERNAME}:{pwd}@{self.CAMERA_IP}:"
            f"{self.CAMERA_RTSP_PORT}{path}"
        )


settings = Settings()
