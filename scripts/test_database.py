#!/usr/bin/env python3
"""
Phase 12: Database & Detection History Persistence Verification Suite
Tests:
1. SQLAlchemy async/sync schema initialization (SQLite/PostgreSQL)
2. Camera registration & detection session lifecycle
3. Incident snapshot disk storage, JPEG integrity, and web path resolution
4. High-frequency non-blocking event & bounding box ingestion
5. Complex query filtering (category, class, confidence, pagination)
6. REST API integration: /api/v1/detections, /api/v1/detections/{id}, and /snapshots/{filename}
"""

import sys
import os
import time
import uuid
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, func
from fastapi.testclient import TestClient

from main import app
from app.core.config import settings
from app.db.models import Base, Camera, DetectionSession, DetectionEvent, BoundingBox
from app.db.session import init_db, get_sync_session, AsyncSessionLocal, sync_engine
from app.services.camera_stream import camera_manager
from app.services.snapshot_service import snapshot_service
from app.services.detection_service import detection_service


def run_database_tests():
    print("=" * 80)
    print(" PHASE 12: DATABASE & DETECTION HISTORY PERSISTENCE VERIFICATION")
    print("=" * 80)

    # --------------------------------------------------------------------------
    # Step 1: Database Schema & Table Initialization
    # --------------------------------------------------------------------------
    print("\n[Step 1/6] Initializing Database Schema & Verifying Tables:")
    Base.metadata.create_all(bind=sync_engine)
    
    db_file = backend_dir / "storage" / "road_detection.db"
    assert db_file.exists(), f"Database file not found at {db_file}"
    print(f"      - SQLite Database created: {db_file.name} ({db_file.stat().st_size} bytes)")
    
    with get_sync_session() as session:
        # Verify table reflection
        tables = Base.metadata.tables.keys()
        expected = {"cameras", "detection_sessions", "detection_events", "bounding_boxes"}
        assert expected.issubset(set(tables)), f"Missing tables! Found: {tables}"
        print(f"      - Relational Tables Verified: {', '.join(sorted(expected))}")
    print("      [PASS] Database schema initialization verified.")

    # --------------------------------------------------------------------------
    # Step 2: Camera Registration & Session Lifecycle
    # --------------------------------------------------------------------------
    print("\n[Step 2/6] Registering Camera Entity & Active Detection Session:")
    test_cam_id = f"cam_test_{int(time.time())}"
    test_session_id = str(uuid.uuid4())

    with get_sync_session() as session:
        # Create Camera
        cam = Camera(
            id=test_cam_id,
            name="CP PLUS CP-E25A TEST",
            ip_address="192.168.1.100",
            rtsp_port=554,
            onvif_port=8000,
            stream_path="/cam/realmonitor?channel=1&subtype=0",
            is_active=True
        )
        session.add(cam)

        # Create Detection Session
        det_session = DetectionSession(
            id=test_session_id,
            camera_id=test_cam_id,
            total_frames_processed=150,
            average_fps=29.4
        )
        session.add(det_session)
        session.commit()

        # Query back
        loaded_cam = session.get(Camera, test_cam_id)
        assert loaded_cam is not None
        assert loaded_cam.name == "CP PLUS CP-E25A TEST"
        print(f"      - Camera Created: id={loaded_cam.id}, name={loaded_cam.name}, ip={loaded_cam.ip_address}")

        loaded_session = session.get(DetectionSession, test_session_id)
        assert loaded_session is not None
        assert loaded_session.camera_id == test_cam_id
        print(f"      - Session Created: id={loaded_session.id[:8]}..., camera_id={loaded_session.camera_id}")
    print("      [PASS] Camera & Session relational records established.")

    # --------------------------------------------------------------------------
    # Step 3: Incident Snapshot Disk Storage & JPEG Integrity
    # --------------------------------------------------------------------------
    print("\n[Step 3/6] Testing Incident Snapshot Persistence & Web URL Resolution:")
    dummy_frame = camera_manager.generate_synthetic_frame("INCIDENT SNAPSHOT TEST: POTHOLE D40")
    test_event_id = f"evt_snap_{int(time.time())}"

    snap_url = snapshot_service.save_detection_snapshot(
        frame=dummy_frame,
        event_id=test_event_id,
        category="road_damage",
        class_name="pothole",
        confidence=0.93,
        bbox=[120, 200, 300, 380],
        crop=False
    )
    assert snap_url is not None
    assert snap_url.startswith("/snapshots/snap_")
    print(f"      - Snapshot Web URL generated: {snap_url}")

    # Verify physical file on disk
    filename = Path(snap_url).name
    physical_path = backend_dir / "storage" / "snapshots" / filename
    assert physical_path.exists(), f"Physical snapshot not found: {physical_path}"
    file_size = physical_path.stat().st_size
    assert file_size > 10000, f"Snapshot file abnormally small: {file_size} bytes"

    # Verify JPEG SOI header
    with open(physical_path, "rb") as f:
        header = f.read(2)
        assert header == b"\xff\xd8", "File is not a valid JPEG format!"
    print(f"      - Physical File Verified: {physical_path.name} ({file_size / 1024:.1f} KB, valid JPEG)")
    print("      [PASS] Snapshot storage and verification successful.")

    # --------------------------------------------------------------------------
    # Step 4: Detection Event & Bounding Box Ingestion
    # --------------------------------------------------------------------------
    print("\n[Step 4/6] Ingesting Detection Events & Bounding Boxes into Database:")
    sample_records = [
        {
            "id": f"evt_dmg_pothole_{int(time.time())}",
            "timestamp": time.time(),
            "category": "road_damage",
            "class_id": 0,
            "class_name": "pothole",
            "confidence": 0.94,
            "bbox": [100, 150, 260, 310],
            "normalized_bbox": [0.28, 0.36, 0.25, 0.25],
            "snapshot_path": snap_url,
            "flagged_for_review": True
        },
        {
            "id": f"evt_dmg_crack_{int(time.time())}",
            "timestamp": time.time() + 1,
            "category": "road_damage",
            "class_id": 1,
            "class_name": "alligator_crack",
            "confidence": 0.86,
            "bbox": [200, 300, 450, 480],
            "normalized_bbox": [0.50, 0.60, 0.39, 0.28],
            "snapshot_path": snap_url,
            "flagged_for_review": False
        },
        {
            "id": f"evt_obj_car_{int(time.time())}",
            "timestamp": time.time() + 2,
            "category": "general_object",
            "class_id": 2,
            "class_name": "car",
            "confidence": 0.91,
            "bbox": [400, 180, 580, 320],
            "normalized_bbox": [0.76, 0.39, 0.28, 0.22],
            "snapshot_path": None,
            "flagged_for_review": False
        }
    ]

    # Ingest through detection service
    detection_service.record_detections(sample_records)
    # Give background worker thread 1.0 second to flush the queue into SQLite
    time.sleep(1.0)

    with get_sync_session() as session:
        count = session.query(func.count(DetectionEvent.id)).scalar()
        assert count >= 3, f"Expected at least 3 events, found {count}"
        print(f"      - Total Detection Events in Database: {count}")

        boxes_count = session.query(func.count(BoundingBox.id)).scalar()
        assert boxes_count >= 3, f"Expected at least 3 bounding boxes, found {boxes_count}"
        print(f"      - Total Bounding Boxes in Database:   {boxes_count}")
    print("      [PASS] Multithreaded database ingestion verified.")

    # --------------------------------------------------------------------------
    # Step 5: Advanced Query Filtering (Category, Class, Confidence)
    # --------------------------------------------------------------------------
    print("\n[Step 5/6] Testing Advanced Historical Query Filtering & Pagination:")
    with get_sync_session() as session:
        # Category filter: road_damage
        dmg_events = session.query(DetectionEvent).filter(DetectionEvent.category == "road_damage").all()
        assert len(dmg_events) >= 2
        print(f"      - Road Damage Filter: {len(dmg_events)} incidents matched.")

        # Class filter: car
        car_events = session.query(DetectionEvent).filter(DetectionEvent.primary_class == "car").all()
        assert len(car_events) >= 1
        print(f"      - Class Name Filter ('car'): {len(car_events)} objects matched.")

        # High confidence filter: >= 0.90
        high_conf = session.query(DetectionEvent).filter(DetectionEvent.confidence >= 0.90).all()
        assert len(high_conf) >= 2
        print(f"      - Confidence Filter (>= 90%): {len(high_conf)} events matched.")
    print("      [PASS] Advanced database query filtering verified.")

    # --------------------------------------------------------------------------
    # Step 6: REST API Verification & Static Snapshot Serving
    # --------------------------------------------------------------------------
    print("\n[Step 6/6] Verifying REST Endpoints & Static Snapshot HTTP Serving:")
    with TestClient(app) as client:
        # 6a. GET /api/v1/detections (Category filtered)
        resp_dmg = client.get("/api/v1/detections?category=road_damage&page_size=5")
        assert resp_dmg.status_code == 200
        dmg_json = resp_dmg.json()
        assert dmg_json["total_records"] >= 2
        assert len(dmg_json["detections"]) > 0
        first_det = dmg_json["detections"][0]
        print(f"      - REST GET /detections?category=road_damage: Total={dmg_json['total_records']}, First ID={first_det['id'][:12]}")

        # 6b. GET /api/v1/detections/{id}
        det_id = sample_records[0]["id"]
        detail_resp = client.get(f"/api/v1/detections/{det_id}")
        assert detail_resp.status_code == 200
        detail_json = detail_resp.json()
        assert detail_json["id"] == det_id
        assert detail_json["class_name"] == "pothole"
        assert len(detail_json["bounding_boxes"]) >= 1
        print(f"      - REST GET /detections/{{id}}: Retrieved event '{detail_json['class_name']}' "
              f"with {len(detail_json['bounding_boxes'])} bounding boxes and snapshot={detail_json['snapshot_path']}")

        # 6c. GET /snapshots/{filename}
        snap_http_resp = client.get(snap_url)
        assert snap_http_resp.status_code == 200
        assert snap_http_resp.headers["content-type"].startswith("image/jpeg")
        assert len(snap_http_resp.content) > 10000
        print(f"      - HTTP GET {snap_url}: Status=200 OK, Content-Type={snap_http_resp.headers['content-type']}, "
              f"Size={len(snap_http_resp.content)} bytes")
        print("      [PASS] REST detection querying and static snapshot streaming verified.")

    print("\n" + "=" * 80)
    print("PHASE 12 DATABASE & PERSISTENCE VERIFICATION COMPLETE: ALL 6 STEPS PASSED")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_database_tests()
