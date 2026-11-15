# ==============================================================================
# AI-Based Road Damage Detection & Object Recognition System
# Production Dockerfile - Optimized for Free Cloud Hosting (Hugging Face / Render / Railway)
# ==============================================================================

FROM python:3.12-slim AS base

# System environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860 \
    APP_ENV=production \
    DEMO_MODE=true \
    DEVICE=cpu

# Install runtime system libraries for OpenCV, image processing, and curl healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root application user (UID 1000 standard for Hugging Face Spaces & security)
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install lightweight CPU-only PyTorch first to keep image slim
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install remaining backend dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source code, models, and assets
COPY --chown=appuser:appuser backend/ /app/

# Ensure runtime storage and snapshot directories exist and are writable
RUN mkdir -p /app/storage/snapshots /app/models /app/assets/demo_frames \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose application ports (8000 for standard FastAPI/Nginx, 7860 for Hugging Face Spaces)
EXPOSE 8000
EXPOSE 7860

# Healthcheck probe for container orchestrators
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-7860}/health || exit 1

# Production command using Uvicorn ASGI server with dynamic port binding
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}"]
