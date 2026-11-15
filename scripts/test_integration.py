#!/usr/bin/env python3
"""
Phase 11: End-to-End Frontend-Backend Integration Verification Suite
Validates synchronized coordination across:
1. REST API endpoints (Camera, Detection, Stats, History)
2. Live WebSocket bidirectional telemetry & command channels
3. MJPEG live visual streaming pipeline
4. Cross-channel event broadcasting (Camera & AI state changes)
"""

import sys
import os
import time
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app
from app.services.camera_stream import camera_manager
from app.services.video_pipeline import video_pipeline
from app.services.detection_service import detection_service


def read_next_event(websocket, target_event: str, max_attempts: int = 10):
    """Helper to poll WebSocket until the target event arrives, ignoring intermediate frames."""
    for _ in range(max_attempts):
        msg = websocket.receive_json()
        if msg.get("event") == target_event:
            return msg
    return None


def run_integration_tests():
    print("=" * 80)
    print(" PHASE 11: FRONTEND-BACKEND INTEGRATION & SYNCHRONIZATION VERIFICATION")
    print("=" * 80)

    with TestClient(app) as client:
        print("\n[Step 1/6] Verifying REST API Base & Static Dashboard Delivery:")
        root_resp = client.get("/")
        assert root_resp.status_code == 200, f"Expected 200 from root, got {root_resp.status_code}"
        assert "ROAD•AI SURVEILLANCE" in root_resp.text
        print("      - Root GET / served HTML dashboard successfully.")

        health_resp = client.get("/health")
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        print(f"      - Health Check: status={health_data.get('status')}, "
              f"camera_connected={health_data.get('camera_connected')}, "
              f"ai_models_loaded={health_data.get('ai_models_loaded')}")
        print("      [PASS] REST API and Static UI service verified.")

        print("\n[Step 2/6] Connecting WebSocket Client & Testing Handshake:")
        with client.websocket_connect("/ws/detections") as ws:
            handshake = ws.receive_json()
            assert handshake.get("event") == "HANDSHAKE_ACK"
            print(f"      - Handshake Event: {handshake.get('event')}")
            print(f"      - Stream Info:     {handshake.get('message')}")
            print("      [PASS] WebSocket client successfully registered.")

            print("\n[Step 3/6] Testing REST -> WebSocket Broadcast for AI Detection State:")
            # 3a. Call REST POST /api/v1/detection/stop
            stop_resp = client.post("/api/v1/detection/stop")
            assert stop_resp.status_code == 200
            assert stop_resp.json()["detection_active"] is False

            event = read_next_event(ws, "DETECTION_STATE_CHANGED")
            assert event is not None, "Did not receive DETECTION_STATE_CHANGED on stop!"
            assert event.get("detection_active") is False
            print(f"      - REST /detection/stop triggered WebSocket broadcast: active={event.get('detection_active')}")

            # 3b. Call REST POST /api/v1/detection/start
            start_resp = client.post("/api/v1/detection/start")
            assert start_resp.status_code == 200
            assert start_resp.json()["detection_active"] is True

            event = read_next_event(ws, "DETECTION_STATE_CHANGED")
            assert event is not None, "Did not receive DETECTION_STATE_CHANGED on start!"
            assert event.get("detection_active") is True
            print(f"      - REST /detection/start triggered WebSocket broadcast: active={event.get('detection_active')}")
            print("      [PASS] AI state REST commands broadcast to WebSocket clients in real-time.")

            print("\n[Step 4/6] Testing REST -> WebSocket Broadcast for Camera State:")
            # 4a. Call REST POST /api/v1/camera/disconnect
            disc_resp = client.post("/api/v1/camera/disconnect")
            assert disc_resp.status_code == 200

            event = read_next_event(ws, "CAMERA_STATUS_CHANGED")
            assert event is not None, "Did not receive CAMERA_STATUS_CHANGED on disconnect!"
            print(f"      - Camera Disconnected event: state={event.get('camera', {}).get('state')}")

            # 4b. Reconnect Camera via REST POST /api/v1/camera/connect
            conn_resp = client.post("/api/v1/camera/connect", json={
                "ip_address": "192.168.1.100",
                "rtsp_port": 554,
                "username": "admin",
                "password": "Password123"
            })
            assert conn_resp.status_code == 200

            event = read_next_event(ws, "CAMERA_STATUS_CHANGED")
            assert event is not None, "Did not receive CAMERA_STATUS_CHANGED on reconnect!"
            print(f"      - Camera Reconnected event: state={event.get('camera', {}).get('state')}")
            print("      [PASS] Camera lifecycle REST events broadcast to WebSocket clients.")

            print("\n[Step 5/6] Testing WebSocket Command Channel & Telemetry Ingestion:")
            # 5a. Send ping command
            ws.send_json({"command": "ping"})
            pong = read_next_event(ws, "PONG")
            assert pong is not None
            print(f"      - WebSocket command Ping received: {pong.get('event')}")

            # 5b. Send toggle_detection command over WebSocket
            ws.send_json({"command": "toggle_detection"})
            toggle_event = read_next_event(ws, "DETECTION_STATE_CHANGED")
            assert toggle_event is not None
            print(f"      - WebSocket toggle_detection returned: active={toggle_event.get('detection_active')}")

            # Restore detection active state
            client.post("/api/v1/detection/start")

            # 5c. Feed synthetic frame and verify detection telemetry streaming
            dummy = camera_manager.generate_synthetic_frame("INTEGRATION_TEST_FRAME")
            video_pipeline.frame_buffer.put(dummy)
            det_update = read_next_event(ws, "DETECTION_UPDATE")
            assert det_update is not None
            print(f"      - Detection Telemetry Received: frame_id={det_update.get('frame_id')}, "
                  f"latency={det_update.get('latency_ms')} ms, fps={det_update.get('fps'):.1f}")
            print("      [PASS] WebSocket bidirectional command dispatch and telemetry verified.")

        print("\n[Step 6/6] Verifying Data Persistence Sync & MJPEG Live Stream Pipeline:")
        # 6a. Record sample test detections into detection service
        sample_detections = [
            {
                "id": f"det_integ_dmg_{int(time.time())}",
                "timestamp": time.time(),
                "category": "road_damage",
                "class_id": 0,
                "class_name": "pothole",
                "confidence": 0.94,
                "bbox": [100, 150, 200, 250],
                "normalized_bbox": [0.23, 0.31, 0.15, 0.15]
            },
            {
                "id": f"det_integ_obj_{int(time.time())}",
                "timestamp": time.time(),
                "category": "general_object",
                "class_id": 2,
                "class_name": "car",
                "confidence": 0.88,
                "bbox": [300, 200, 450, 320],
                "normalized_bbox": [0.58, 0.40, 0.23, 0.18]
            }
        ]
        detection_service.record_detections(sample_detections)

        # 6b. Verify REST API /api/v1/detections returns recorded items
        hist_resp = client.get("/api/v1/detections?page_size=5")
        assert hist_resp.status_code == 200
        hist_data = hist_resp.json()
        assert hist_data["total_records"] >= 2
        print(f"      - REST /detections returned {hist_data['total_records']} total historical items.")

        # 6c. Verify REST API /api/v1/statistics aggregates correctly
        stats_resp = client.get("/api/v1/statistics")
        assert stats_resp.status_code == 200
        stats_data = stats_resp.json()
        assert stats_data["total_road_damages"] >= 1
        assert stats_data["total_objects"] >= 1
        print(f"      - REST /statistics: Damages={stats_data['total_road_damages']}, "
              f"Objects={stats_data['total_objects']}")

        # 6d. Verify MJPEG stream frame generation
        gen = detection_service.generate_mjpeg_stream()
        first_chunk = next(gen)
        assert b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" in first_chunk
        assert b"\xff\xd8" in first_chunk  # Valid JPEG SOI marker
        print(f"      - MJPEG stream validated: Frame chunk size={len(first_chunk)} bytes with valid JPEG SOI.")
        print("      [PASS] Data persistence sync and MJPEG live stream pipeline verified.")

    print("\n" + "=" * 80)
    print("PHASE 11 INTEGRATION VERIFICATION COMPLETE: ALL 6 STEPS PASSED (100%)")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_integration_tests()
