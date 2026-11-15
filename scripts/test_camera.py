#!/usr/bin/env python3
"""
CP PLUS CP-E25A Camera Diagnostic & Stream Testing Utility
Executes socket tests, stream profile discovery, frame reading, and snapshot capture.
"""

import sys
import os
import time
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import cv2
from app.core.config import settings
from app.core.logging import logger
from app.services.camera_stream import camera_manager, CameraState


def run_diagnostics():
    print("=" * 75)
    print("CP PLUS CP-E25A CAMERA CONNECTIVITY & RTSP STREAM DIAGNOSTIC SUITE")
    print("=" * 75)

    host = settings.CAMERA_IP
    rtsp_port = settings.CAMERA_RTSP_PORT
    onvif_port = settings.CAMERA_ONVIF_PORT
    snapshot_dir = backend_dir / settings.SNAPSHOT_DIR
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[1/4] Network Reachability Diagnostics for {host}:")
    # RTSP Port (554)
    rtsp_ok, rtsp_msg = camera_manager.test_network_reachability(host, rtsp_port, timeout=2.5)
    print(f"      - RTSP Port ({rtsp_port}):  {'[REACHABLE]' if rtsp_ok else '[FAILED]'} -> {rtsp_msg}")

    # ONVIF / Management Port (8000 or 80)
    onvif_ok, onvif_msg = camera_manager.test_network_reachability(host, onvif_port, timeout=2.5)
    print(f"      - ONVIF Port ({onvif_port}): {'[REACHABLE]' if onvif_ok else '[FAILED]'} -> {onvif_msg}")

    if not rtsp_ok:
        print("\n[NOTE] Physical CP PLUS camera is currently unreachable on this local IP.")
        print(f"       IP Configured in .env: {host}:{rtsp_port}")
        print("       (Refer to docs/camera_setup.md to find or set your camera's IP address)")

    print("\n[2/4] Profile & Stream Discovery Probe:")
    if rtsp_ok:
        discovered_url, report = camera_manager.discover_stream_profile(host, rtsp_port)
        if discovered_url:
            print(f"      [SUCCESS] Active stream discovered: {camera_manager._mask_url(discovered_url)}")
            for p in report["tested_profiles"]:
                print(f"                - {p['url']}: {p['status']} ({p.get('resolution', '')} @ {p.get('fps', '')} FPS)")
        else:
            print("      [WARNING] RTSP port responded, but no tested stream paths produced video frames.")
            for p in report["tested_profiles"]:
                print(f"                - {p['url']}: {p['status']}")
    else:
        print("      Skipping active RTSP discovery (Port 554 unreachable). Testing synthetic fallback stream.")

    print("\n[3/4] Testing Video Frame Acquisition:")
    snapshot_path = snapshot_dir / "camera_test_snapshot.jpg"

    if rtsp_ok and (settings.CAMERA_RTSP_OVERRIDE_URL or rtsp_ok):
        print(f"      Attempting live frame capture from {camera_manager._mask_url(settings.get_rtsp_url())}...")
        connected = camera_manager.connect()
        if connected:
            time.sleep(1.0)  # Allow buffer to fill
            ret, frame = camera_manager.get_latest_frame()
            if ret and frame is not None:
                cv2.imwrite(str(snapshot_path), frame)
                h, w = frame.shape[:2]
                print(f"      [SUCCESS] Frame captured: {w}x{h} px")
                print(f"                Saved snapshot to: {snapshot_path}")
            else:
                print("      [ERROR] Could not grab frame from connected stream.")
            camera_manager.disconnect()
        else:
            print(f"      [ERROR] Connection failed: {camera_manager.last_error}")
    else:
        print("      Generating synthetic road surveillance frame for offline validation...")
        synth_frame = camera_manager.generate_synthetic_frame(
            "OFFLINE SIMULATION | READY FOR CAMERA AT " + host
        )
        cv2.imwrite(str(snapshot_path), synth_frame)
        h, w = synth_frame.shape[:2]
        print(f"      [PASS] Synthetic stream engine operational: {w}x{h} px")
        print(f"             Saved sample snapshot to: {snapshot_path}")

    print("\n[4/4] Camera Manager Status Snapshot:")
    info = camera_manager.stream_info
    for k, v in info.items():
        print(f"      - {k:<25}: {v}")

    print("\n" + "=" * 75)
    print("DIAGNOSTIC SUMMARY & NEXT STEPS")
    print("=" * 75)
    if rtsp_ok:
        print(">> Physical camera is online and responding over RTSP.")
    else:
        print(">> Physical camera offline or not on current subnet. Synthetic fallback verified.")
        print(f">> When connecting camera, edit .env to set CAMERA_IP, CAMERA_USERNAME, CAMERA_PASSWORD.")
        print(">> Detailed setup instructions: docs/camera_setup.md")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_diagnostics()
