#!/usr/bin/env python3
"""
Phase 14: Master End-to-End Test Runner & System Verification Scorecard
Executes all 12 test suites sequentially, benchmarks system performance,
and outputs a comprehensive production readiness verification report.
"""

import sys
import os
import time
import subprocess
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
python_exe = sys.executable

TEST_SUITES = [
    {
        "phase": "Phase 2",
        "name": "Environment & Dependency Verification",
        "script": "scripts/verify_env.py",
        "scope": "Python 3.12, PyTorch, YOLO, OpenCV, FastAPI, DB drivers"
    },
    {
        "phase": "Phase 3",
        "name": "CP PLUS Camera Connection & Ingestion",
        "script": "scripts/test_camera.py",
        "scope": "RTSP profiles, credential masking, pre-flight TCP probe"
    },
    {
        "phase": "Phase 4",
        "name": "OpenCV Pipeline & Low-Latency Buffer",
        "script": "scripts/test_video_pipeline.py",
        "scope": "Zero-latency ring buffer, letterboxing, HUD overlay"
    },
    {
        "phase": "Phase 5",
        "name": "YOLO General Object Detection",
        "script": "scripts/test_general_detection.py",
        "scope": "YOLOv8n inference, traffic class filtering (COCO)"
    },
    {
        "phase": "Phase 6",
        "name": "Custom Road Damage AI Model",
        "script": "scripts/test_road_damage_detection.py",
        "scope": "Potholes (D40), Cracks (D00, D10, D20) classification"
    },
    {
        "phase": "Phase 7",
        "name": "Simultaneous Dual-Inference Engine",
        "script": "scripts/test_simultaneous_detection.py",
        "scope": "Concurrent dual YOLO inference, IoU fusion & HUD"
    },
    {
        "phase": "Phase 8",
        "name": "FastAPI REST API Endpoints",
        "script": "scripts/test_api.py",
        "scope": "10 REST endpoints, Pydantic schemas, MJPEG stream"
    },
    {
        "phase": "Phase 9",
        "name": "Real-Time WebSocket Communication",
        "script": "scripts/test_websocket.py",
        "scope": "Bidirectional WS channel, ping/pong, telemetry feed"
    },
    {
        "phase": "Phase 10",
        "name": "Frontend Dashboard Delivery",
        "script": "scripts/test_frontend.py",
        "scope": "7 dashboard pages, static assets, React structure"
    },
    {
        "phase": "Phase 11",
        "name": "Frontend-Backend Integration",
        "script": "scripts/test_integration.py",
        "scope": "REST -> WS event broadcasts, synchronized controls"
    },
    {
        "phase": "Phase 12",
        "name": "Database & Detection Persistence",
        "script": "scripts/test_database.py",
        "scope": "SQLAlchemy ORM, snapshots, query filtering, SQLite WAL"
    },
    {
        "phase": "Phase 13",
        "name": "Deployment & Security Hardening",
        "script": "scripts/test_deployment_config.py",
        "scope": "Docker, Compose, Nginx, Cloudflare, API Key guard"
    }
]


def run_master_test_suite():
    print("=" * 90)
    print(" AI ROAD DAMAGE & OBJECT RECOGNITION SYSTEM - MASTER VERIFICATION RUNNER")
    print("=" * 90)
    print(f"Working Directory : {project_root}")
    print(f"Python Runtime    : {sys.version.split()[0]} ({python_exe})")
    print(f"Total Test Suites : {len(TEST_SUITES)}")
    print("=" * 90 + "\n")

    results = []
    total_start = time.time()

    for idx, test in enumerate(TEST_SUITES, 1):
        script_path = project_root / test["script"]
        print(f"[{idx:02d}/{len(TEST_SUITES):02d}] Executing {test['phase']}: {test['name']}...", flush=True)
        start_t = time.time()

        try:
            cmd = [python_exe, "-u", str(script_path)]
            proc = subprocess.run(
                cmd,
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=45
            )
            duration = time.time() - start_t
            success = proc.returncode == 0

            status_str = "PASSED" if success else "FAILED"
            print(f"       -> Status: [{status_str}] in {duration:.2f}s", flush=True)
            if not success:
                print(f"\n--- Error Trace ({test['script']}) ---", flush=True)
                lines = proc.stdout.splitlines()[-15:]
                print("\n".join(lines), flush=True)
                print("-" * 50 + "\n", flush=True)

            results.append({
                "phase": test["phase"],
                "name": test["name"],
                "scope": test["scope"],
                "duration": duration,
                "status": status_str,
                "passed": success
            })
        except Exception as e:
            duration = time.time() - start_t
            print(f"       -> Status: [ERROR] ({e})")
            results.append({
                "phase": test["phase"],
                "name": test["name"],
                "scope": test["scope"],
                "duration": duration,
                "status": "ERROR",
                "passed": False
            })

    total_duration = time.time() - total_start
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)

    # Print Master Scorecard
    print("\n" + "=" * 90)
    print(" MASTER SYSTEM VERIFICATION SCORECARD")
    print("=" * 90)
    print(f"{'Phase':<10} | {'Test Suite Name':<38} | {'Duration':<9} | {'Status':<8}")
    print("-" * 90)
    for r in results:
        status_marker = "[PASS]" if r["passed"] else "[FAIL]"
        print(f"{r['phase']:<10} | {r['name'][:38]:<38} | {r['duration']:>6.2f}s  | {status_marker}")
    print("-" * 90)
    print(f"TOTAL RESULT: {passed_count}/{total_count} PASSED ({passed_count/total_count*100:.1f}%) in {total_duration:.2f}s")
    print("=" * 90 + "\n")

    if passed_count == total_count:
        print(">> ALL SYSTEM SUBSYSTEMS FULLY OPERATIONAL AND VERIFIED FOR PRODUCTION <<\n")
        return 0
    else:
        print(">> SOME SUBSYSTEMS FAILED VERIFICATION - REVIEW LOGS ABOVE <<\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_master_test_suite())
