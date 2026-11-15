#!/usr/bin/env python3
"""
Live Camera Inference & Pipeline Benchmark
Tests frame capture from the configured RTSP stream and measures dual YOLO inference latency.
Skips gracefully if the camera is offline.
"""

import sys
import os
import time
from pathlib import Path
import cv2

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.core.config import settings
from app.services.dual_detector import dual_engine
from app.services.camera_stream import camera_manager


def run_live_inference_test():
    rtsp_url = settings.get_rtsp_url()
    host = settings.CAMERA_IP
    port = settings.CAMERA_RTSP_PORT

    print(f"Target stream: {camera_manager._mask_url(rtsp_url)}")
    if not host or not port:
        print("[SKIP] No camera host or port configured. Skipping.")
        return 0

    is_reachable, reach_msg = camera_manager.test_network_reachability(host, port, timeout=1.0)
    if not is_reachable:
        print(f"[SKIP] Camera unreachable at {host}:{port}: {reach_msg}. Skipping gracefully.")
        return 0

    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print(f"[SKIP] Failed to open RTSP stream at {camera_manager._mask_url(rtsp_url)}. Skipping gracefully.")
        cap.release()
        return 0

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        print("[SKIP] Opened stream but failed to read initial frame. Skipping gracefully.")
        return 0

    print(f"Captured live frame: {frame.shape[1]}x{frame.shape[0]}")
    for i in range(3):
        detections, telemetry = dual_engine.process_frame(frame)
        print(
            f"  Run {i+1}: Latency: {telemetry['latency_ms']:.1f}ms "
            f"(DMG: {telemetry['damage_latency_ms']:.1f}ms, OBJ: {telemetry['object_latency_ms']:.1f}ms) "
            f"Detections: {len(detections)}"
        )

    # Save output to backend storage if directory exists
    out_dir = PROJECT_ROOT / "backend" / "storage" / "snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "latest_live_test.jpg"
    cv2.imwrite(str(out_file), frame)
    print(f"Snapshot saved to: {out_file.name}")
    print("[PASS] Live inference test completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(run_live_inference_test())
