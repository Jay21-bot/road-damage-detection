"""
Security & Authentication Module
Provides API Key authentication and token verification for administrative camera controls.
Ensures zero-credential camera exposure and protects sensitive edge operations.
"""

from typing import Optional
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

from app.core.config import settings
from app.core.logging import logger

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> bool:
    """
    Validates the X-API-Key header for sensitive camera control and AI state toggle endpoints.
    - In production (APP_ENV == 'production'), strictly validates X-API-Key against API_SECRET_KEY.
    - In development, allows bypass only if API_SECRET_KEY is explicitly marked as insecure.
    """
    configured_key = settings.API_SECRET_KEY
    is_prod = settings.APP_ENV.lower() == "production"

    if not is_prod and (not configured_key or "change_in_production" in configured_key.lower()):
        return True

    if not api_key:
        logger.warning("Unauthorized access attempt: Missing X-API-Key header.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required 'X-API-Key' authentication header. Admin privileges required."
        )

    if api_key != configured_key:
        logger.warning("Unauthorized access attempt: Invalid X-API-Key provided.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid 'X-API-Key' credential."
        )

    return True
