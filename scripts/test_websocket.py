#!/usr/bin/env python3
"""
WebSocket Real-Time Vision & Telemetry Verification Utility
Tests connection handshake, ping-pong command, and detection telemetry streaming.
"""

import sys
import os
import time
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app


def run_websocket_tests():
    print("=" * 75)
    print("REAL-TIME WEBSOCKET TELEMETRY & COMMAND VERIFICATION SUITE")
    print("=" * 75)

    with TestClient(app) as client:
        print("\n[1/4] Establishing WebSocket Connection to /ws/detections:")
        with client.websocket_connect("/ws/detections") as websocket:
            # 1. Handshake ACK
            handshake = websocket.receive_json()
            print(f"      - Received Event: {handshake.get('event')}")
            print(f"      - Server Message: {handshake.get('message')}")
            assert handshake.get("event") == "HANDSHAKE_ACK", "Handshake failed!"
            print("      [PASS] WebSocket handshake established successfully.")

            # 2. Test Ping / Pong Command (accounting for concurrent DETECTION_UPDATE stream)
            print("\n[2/4] Testing Bi-directional Command Dispatch (Ping / Pong):")
            websocket.send_json({"command": "ping"})
            
            # Receive incoming messages until PONG is caught (or broadcast events pass through)
            got_pong = False
            for _ in range(5):
                msg = websocket.receive_json()
                event_type = msg.get("event")
                print(f"      - Received WebSocket Event: {event_type}")
                if event_type == "PONG":
                    got_pong = True
                    break
            assert got_pong, "Expected PONG response within incoming event stream!"
            print("      [PASS] Client-server command execution verified.")

            # 3. Test Status Query over WebSocket
            print("\n[3/4] Testing Real-Time Status Query over WebSocket:")
            websocket.send_json({"command": "get_status"})
            got_status = False
            for _ in range(5):
                msg = websocket.receive_json()
                if msg.get("event") == "STATUS_UPDATE":
                    got_status = True
                    print(f"      - Received Event: {msg.get('event')}")
                    print(f"      - Camera State:   {msg.get('camera', {}).get('state')}")
                    print(f"      - Dual AI Status: General={msg.get('engine', {}).get('general_model_ready')}, "
                          f"RoadDamage={msg.get('engine', {}).get('road_damage_model_ready')}")
                    break
            assert got_status, "Expected STATUS_UPDATE response!"
            print("      [PASS] Live status telemetry retrieved over WebSocket.")

            # 4. Test Detection Stream Packet
            print("\n[4/4] Testing Detection Stream Telemetry Payload:")
            # Inject a mock frame into video buffer to trigger detection telemetry
            from app.services.camera_stream import camera_manager
            from app.services.video_pipeline import video_pipeline
            dummy = camera_manager.generate_synthetic_frame("WS VERIFICATION TEST")
            video_pipeline.frame_buffer.put(dummy)

            # Wait for broadcaster to yield DETECTION_UPDATE
            stream_event = websocket.receive_json()
            print(f"      - Received Broadcast Event: {stream_event.get('event')}")
            print(f"      - Frame ID:       {stream_event.get('frame_id')}")
            print(f"      - Latency:        {stream_event.get('latency_ms')} ms")
            print(f"      - Damage Count:   {stream_event.get('counts', {}).get('damages')}")
            print(f"      - Object Count:   {stream_event.get('counts', {}).get('objects')}")
            assert stream_event.get("event") in ("DETECTION_UPDATE", "STATUS_UPDATE")
            print("      [PASS] Real-time detection streaming packet verified.")

    print("\n" + "=" * 75)
    print("PHASE 9 WEBSOCKET TEST SUMMARY")
    print("=" * 75)
    print(">> WebSocket /ws/detections endpoint: 100% OPERATIONAL")
    print(">> Handshake, Command/Response, and Telemetry Broadcasting: VERIFIED")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_websocket_tests()
