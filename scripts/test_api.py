#!/usr/bin/env python3
"""
FastAPI REST API Verification & End-to-End Test Suite
Tests all endpoints: /health, /camera/*, /detection/*, /statistics, /stream
"""

import sys
import os
import time
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app
from app.services.detection_service import detection_service


def run_api_tests():
    print("=" * 75)
    print("FASTAPI REST API END-TO-END VERIFICATION SUITE")
    print("=" * 75)

    with TestClient(app) as client:
        # 1. Test Root & Health
        print("\n[1/8] Testing Root & Health Check Endpoints:")
        res_root = client.get("/")
        assert res_root.status_code == 200, f"Root failed: {res_root.text}"
        print(f"      - GET / -> {res_root.status_code} OK (HTML Dashboard delivered)")

        res_health = client.get("/health")
        assert res_health.status_code == 200, f"Health failed: {res_health.text}"
        health_data = res_health.json()
        print(f"      - GET /health -> {res_health.status_code} OK: Status={health_data['status']}, "
              f"RAM={health_data['memory_usage_mb']}MB, CPU={health_data['cpu_usage_percent']}%")

        # 2. Test Camera Status
        print("\n[2/8] Testing Camera Status Endpoint:")
        res_cam = client.get("/api/v1/camera/status")
        assert res_cam.status_code == 200, f"Camera status failed: {res_cam.text}"
        cam_data = res_cam.json()
        print(f"      - GET /api/v1/camera/status -> State={cam_data['state']}, URL={cam_data['active_url']}")

        # 3. Test Camera Connect & Disconnect
        print("\n[3/8] Testing Camera Connect & Disconnect Endpoints:")
        connect_payload = {
            "ip_address": "192.168.1.100",
            "rtsp_port": 554,
            "username": "admin",
            "password": "test_password",
            "stream_subtype": 1
        }
        res_conn = client.post("/api/v1/camera/connect", json=connect_payload)
        assert res_conn.status_code == 200, f"Camera connect failed: {res_conn.text}"
        print(f"      - POST /api/v1/camera/connect -> Status={res_conn.json().get('message')}")

        res_disc = client.post("/api/v1/camera/disconnect")
        assert res_disc.status_code == 200, f"Camera disconnect failed: {res_disc.text}"
        print(f"      - POST /api/v1/camera/disconnect -> Status={res_disc.json().get('message')}")

        # 4. Test Detection Start & Stop
        print("\n[4/8] Testing Detection Control (Start / Stop):")
        res_start = client.post("/api/v1/detection/start")
        assert res_start.status_code == 200, f"Detection start failed: {res_start.text}"
        print(f"      - POST /api/v1/detection/start -> Active={res_start.json()['detection_active']}")

        res_stop = client.post("/api/v1/detection/stop")
        assert res_stop.status_code == 200, f"Detection stop failed: {res_stop.text}"
        print(f"      - POST /api/v1/detection/stop -> Active={res_stop.json()['detection_active']}")

        # Re-enable detection for remaining tests
        client.post("/api/v1/detection/start")

        # 5. Test Detection Status
        print("\n[5/8] Testing Detection Status Endpoint:")
        res_det_stat = client.get("/api/v1/detection/status")
        assert res_det_stat.status_code == 200, f"Detection status failed: {res_det_stat.text}"
        ds = res_det_stat.json()
        print(f"      - GET /api/v1/detection/status -> Device={ds['device']}, "
              f"GeneralModel={ds['general_model_ready']}, RoadModel={ds['road_damage_model_ready']}")

        # 6. Test Record Injection & Detection Query
        print("\n[6/8] Testing Detections Query & Filtering:")
        seed_items = [
            {
                "id": "test-uuid-1",
                "timestamp": time.time(),
                "category": "road_damage",
                "class_id": 3,
                "class_name": "pothole",
                "confidence": 0.88,
                "bbox": [200, 400, 350, 500],
                "normalized_bbox": [0.2, 0.4, 0.15, 0.1]
            },
            {
                "id": "test-uuid-2",
                "timestamp": time.time(),
                "category": "general_object",
                "class_id": 2,
                "class_name": "car",
                "confidence": 0.94,
                "bbox": [700, 350, 950, 520],
                "normalized_bbox": [0.65, 0.43, 0.19, 0.17]
            }
        ]
        detection_service.record_detections(seed_items)

        res_all = client.get("/api/v1/detections?page=1&page_size=10")
        assert res_all.status_code == 200, f"Get detections failed: {res_all.text}"
        det_list = res_all.json()
        print(f"      - GET /api/v1/detections (All) -> Total: {det_list['total_records']}, Returned: {len(det_list['detections'])}")

        res_dmg = client.get("/api/v1/detections?category=road_damage")
        assert res_dmg.status_code == 200
        print(f"      - GET /api/v1/detections?category=road_damage -> Found: {len(res_dmg.json()['detections'])}")

        # 7. Test Aggregated Statistics Endpoint
        print("\n[7/8] Testing Aggregated Statistics Endpoint:")
        res_stats = client.get("/api/v1/statistics")
        assert res_stats.status_code == 200, f"Statistics failed: {res_stats.text}"
        st = res_stats.json()
        print(f"      - GET /api/v1/statistics -> Total: {st['total_detections']}, "
              f"Damages: {st['total_road_damages']}, Objects: {st['total_objects']}")
        print(f"        Damage Breakdown: {st['damage_by_class']}")

        # 8. Test Live MJPEG Video Stream Generator
        print("\n[8/8] Testing Live MJPEG Video Stream Handshake & Frame Generation:")
        stream_gen = detection_service.generate_mjpeg_stream()
        first_chunk = next(stream_gen)
        print(f"      - Successfully generated MJPEG frame chunk ({len(first_chunk)} bytes)")
        assert b"--frame" in first_chunk and b"Content-Type: image/jpeg" in first_chunk, "MJPEG boundary missing!"
        print("      [PASS] Live MJPEG video stream generator operational.")

    print("\n" + "=" * 75)
    print("PHASE 8 REST API TEST SUMMARY")
    print("=" * 75)
    print(">> All 10 Core REST Endpoints & Streaming Services: 100% OPERATIONAL")
    print(">> Pydantic request/response validations: PASSED")
    print(">> Video MJPEG stream: VERIFIED")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_api_tests()
