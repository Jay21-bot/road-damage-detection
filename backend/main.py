"""
FastAPI Application Entrypoint
AI-Based Road Damage Detection and Real-Time Object Recognition System
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from app.core.config import settings
from app.core.logging import logger
from app.db.session import init_db
from app.services.video_pipeline import video_pipeline
from app.services.camera_stream import camera_manager
from app.api.v1 import camera, detection, stats, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup initialization and graceful shutdown."""
    logger.info("Initializing AI Road Detection Backend Services...")
    # Initialize SQLite/PostgreSQL Database Schema
    await init_db()
    # Auto-connect physical CP PLUS camera if available
    try:
        logger.info("Attempting auto-connection to CP PLUS CP-E25A camera...")
        connected = camera_manager.connect()
        if connected:
            logger.info(f"Auto-connected to camera stream: {camera_manager.stream_info['active_url']}")
        else:
            logger.info("Camera not reachable at startup; using synthetic fallback stream.")
    except Exception as e:
        logger.warning(f"Camera auto-connect error (using fallback): {e}")
    # Start video ingestion pipeline
    video_pipeline.start()
    logger.info("Application ready to accept API and streaming connections.")
    yield
    logger.info("Initiating graceful shutdown...")
    video_pipeline.stop()
    camera_manager.disconnect()
    logger.info("All video workers and background tasks terminated.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Edge-to-Cloud AI Surveillance & Road Damage Detection System",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

from collections import defaultdict
import threading

# Lightweight IP rate limiting middleware (120 requests / min per IP)
_rate_limit_records = defaultdict(list)
_rate_limit_lock = threading.Lock()

# Configure Cross-Origin Resource Sharing (CORS) restricted to authorized origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins() if settings.APP_ENV == "production" else ["*"],
    allow_origin_regex=r"^https://([a-zA-Z0-9-]+\.)*(hf\.space|huggingface\.co|onrender\.com|railway\.app)$" if settings.APP_ENV == "production" else None,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    """Enforces 120 requests/min per IP to protect public API endpoints while bypassing stream."""
    path = request.url.path
    if path.startswith("/static") or path == "/api/v1/camera/stream" or path == "/health":
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    max_requests = 120

    with _rate_limit_lock:
        timestamps = [t for t in _rate_limit_records[client_ip] if now - t < 60.0]
        if len(timestamps) >= max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Rate limit is 120 requests per minute per IP."}
            )
        timestamps.append(now)
        _rate_limit_records[client_ip] = timestamps

    return await call_next(request)


from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# Static Files Directory
static_dir = Path(__file__).resolve().parent / "app" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Mount Incident Snapshots Directory for Dashboard Visualization
snapshots_dir = Path(__file__).resolve().parent / "storage" / "snapshots"
snapshots_dir.mkdir(parents=True, exist_ok=True)
app.mount("/snapshots", StaticFiles(directory=str(snapshots_dir)), name="snapshots")

# Mount API Routers under /api/v1 prefix
app.include_router(camera.router, prefix=settings.API_V1_PREFIX)
app.include_router(detection.router, prefix=settings.API_V1_PREFIX)
app.include_router(stats.router, prefix=settings.API_V1_PREFIX)
app.include_router(ws.router, prefix=settings.API_V1_PREFIX)
app.include_router(ws.router)  # Also available directly at /ws/detections

# Top-level health check endpoint for cloud load balancers and orchestrators
@app.get("/health", tags=["Root Health Check"])
async def root_health():
    """Root health check endpoint."""
    return await stats.get_health()


@app.get("/", response_class=HTMLResponse, tags=["Dashboard"])
@app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
async def dashboard():
    """Serves the integrated React-styled AI surveillance dashboard."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>AI Road Detection Dashboard</h1>")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
    )
