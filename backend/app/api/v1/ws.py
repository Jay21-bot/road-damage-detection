"""
WebSocket Real-Time Vision & Telemetry Router
Provides live bi-directional communication between frontend clients and AI pipeline.
"""

import time
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import logger
from app.services.websocket_manager import ws_manager
from app.services.camera_stream import camera_manager
from app.services.dual_detector import dual_engine
from app.services.video_pipeline import video_pipeline
from app.services.detection_service import detection_service

router = APIRouter(tags=["WebSocket Real-Time Telemetry"])


@router.websocket("/ws/detections")
async def websocket_detections_endpoint(websocket: WebSocket):
    """
    Real-time WebSocket feed for AI bounding box telemetry, camera state, and FPS metrics.
    Clients can also send operational commands over this connection:
      - {"command": "ping"}
      - {"command": "toggle_detection"}
      - {"command": "get_status"}
    """
    await ws_manager.connect(websocket)

    async def client_receiver():
        """Handles incoming messages and commands from the client."""
        try:
            while True:
                data = await websocket.receive_json()
                command = data.get("command", "").lower()

                if command == "ping":
                    await websocket.send_json({
                        "event": "PONG",
                        "timestamp": time.time()
                    })
                elif command == "toggle_detection":
                    new_state = not detection_service.is_active
                    detection_service.set_active(new_state)
                    await websocket.send_json({
                        "event": "DETECTION_STATE_CHANGED",
                        "detection_active": new_state
                    })
                elif command == "set_mode":
                    new_mode = data.get("mode", "all")
                    dual_engine.set_mode(new_mode)
                    await websocket.send_json({
                        "event": "MODE_CHANGED",
                        "mode": new_mode
                    })
                elif command == "set_thresholds":
                    dual_engine.set_thresholds(
                        damage_conf=data.get("damage_conf"),
                        object_conf=data.get("object_conf")
                    )
                    await websocket.send_json({
                        "event": "THRESHOLDS_CHANGED",
                        "damage_conf": dual_engine.road_damage_conf,
                        "object_conf": dual_engine.general_object_conf
                    })
                elif command == "get_status":
                    await websocket.send_json({
                        "event": "STATUS_UPDATE",
                        "camera": camera_manager.stream_info,
                        "engine": dual_engine.status,
                        "stats": detection_service.get_statistics()
                    })
                else:
                    await websocket.send_json({
                        "event": "UNKNOWN_COMMAND",
                        "received": data
                    })
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.warning(f"WebSocket client receiver error: {e}")

    async def telemetry_broadcaster():
        """Continuously streams high-frequency detection results to the client without redundant inference."""
        try:
            while True:
                detections = dual_engine.get_latest_detections() if detection_service.is_active else []
                telemetry = dual_engine.get_latest_telemetry()

                payload = {
                    "event": "DETECTION_UPDATE",
                    "timestamp": time.time(),
                    "frame_id": telemetry.get("frame_id", 0),
                    "fps": video_pipeline.stats.get("current_fps", 0.0),
                    "latency_ms": telemetry.get("latency_ms", 0.0),
                    "camera_state": camera_manager.state.value,
                    "mode": dual_engine.mode,
                    "counts": {
                        "damages": telemetry.get("damage_count", 0),
                        "objects": telemetry.get("object_count", 0),
                        "total": telemetry.get("total_detections", 0)
                    },
                    "detections": detections
                }
                await websocket.send_json(payload)

                # Broadcast telemetry rate at ~25 Hz
                await asyncio.sleep(0.04)
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.debug(f"Telemetry broadcaster finished: {e}")

    # Run receiver and broadcaster concurrently
    receiver_task = asyncio.create_task(client_receiver())
    broadcaster_task = asyncio.create_task(telemetry_broadcaster())

    try:
        # Wait until either task completes or disconnect occurs
        done, pending = await asyncio.wait(
            [receiver_task, broadcaster_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
    finally:
        await ws_manager.disconnect(websocket)
