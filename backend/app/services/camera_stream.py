"""
CP PLUS CP-E25A Camera Stream & Diagnostics Service
Provides RTSP stream connection, profile discovery, health monitoring,
resilient reconnection, and synthetic stream fallback.
"""

import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|fflags;nobuffer|max_delay;500000"
import time
import socket
import threading
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum
import cv2
import numpy as np

from app.core.config import settings
from app.core.logging import logger


class CameraState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    STREAMING = "STREAMING"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"


class CameraStreamManager:
    """
    Manages connection lifecycle, frame acquisition, and diagnostics
    for the CP PLUS CP-E25A IP Camera.
    """

    KNOWN_CP_PLUS_PATHS = [
        # CP-E25A Happytimesoft RTSP Paths
        "/live/channel0",
        "/live/channel1",
        # Dahua / CP PLUS Primary Stream (1080p)
        "/cam/realmonitor?channel=1&subtype=0",
        # Dahua / CP PLUS Sub-Stream (SD / 360p - low bandwidth)
        "/cam/realmonitor?channel=1&subtype=1",
        # Generic H.264 stream profile
        "/live/ch0",
        # Standard ONVIF profile
        "/onvif1"
    ]

    def __init__(self):
        self._state: CameraState = CameraState.DISCONNECTED
        self._lock = threading.Lock()
        self._cap: Optional[cv2.VideoCapture] = None
        self._active_rtsp_url: Optional[str] = None
        self._last_error: Optional[str] = None
        self._reconnect_count = 0
        self._frame_count = 0
        self._stream_fps: float = 0.0
        self._stream_resolution: Tuple[int, int] = (0, 0)
        self._last_frame: Optional[np.ndarray] = None
        self._last_frame_time: float = 0.0
        self._stop_requested = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._is_demo_active = False
        self._demo_frames: List[np.ndarray] = []
        self._load_demo_frames()

    def _load_demo_frames(self):
        """Loads bundled road damage images for demo simulation."""
        try:
            from pathlib import Path
            assets_dir = Path(__file__).resolve().parent.parent.parent / "assets" / "demo_frames"
            if assets_dir.exists():
                files = sorted(list(assets_dir.glob("*.jpg")))
                for f in files:
                    img = cv2.imread(str(f))
                    if img is not None:
                        self._demo_frames.append(img)
            logger.info(f"Loaded {len(self._demo_frames)} road damage demo frames.")
        except Exception as e:
            logger.warning(f"Could not load demo frames: {e}")

    @property
    def is_demo(self) -> bool:
        with self._lock:
            return settings.DEMO_MODE or self._is_demo_active

    @property
    def state(self) -> CameraState:
        with self._lock:
            return self._state

    @property
    def last_error(self) -> Optional[str]:
        with self._lock:
            return self._last_error

    @property
    def stream_info(self) -> Dict[str, Any]:
        with self._lock:
            active_is_demo = settings.DEMO_MODE or self._is_demo_active
            return {
                "state": self._state.value,
                "demo_mode": active_is_demo,
                "is_synthetic": active_is_demo,
                "active_url": self._mask_url(self._active_rtsp_url) if self._active_rtsp_url else ("DEMO_ROAD_STREAM" if active_is_demo else None),
                "resolution": f"{self._stream_resolution[0]}x{self._stream_resolution[1]}",
                "fps": round(self._stream_fps, 2),
                "frames_received": self._frame_count,
                "reconnect_attempts": self._reconnect_count,
                "last_error": self._last_error,
                "last_frame_age_seconds": round(time.time() - self._last_frame_time, 2) if self._last_frame_time else None
            }

    @staticmethod
    def _mask_url(url: Optional[str]) -> Optional[str]:
        """Masks sensitive credentials in RTSP URL strings."""
        if not url:
            return None
        try:
            if "@" in url and "://" in url:
                scheme, rest = url.split("://", 1)
                user_pass, host_path = rest.split("@", 1)
                if ":" in user_pass:
                    username, _ = user_pass.split(":", 1)
                    return f"{scheme}://{username}:********@{host_path}"
                return f"{scheme}://********@{host_path}"
        except Exception:
            return "rtsp://[MASKED_CREDENTIALS]@"
        return url

    @staticmethod
    def auto_discover_camera_ip() -> Optional[str]:
        """
        Scans local ARP table to locate the CP PLUS camera IP dynamically
        if the configured IP changed due to router DHCP or network switch.
        """
        import subprocess
        import re
        try:
            out = subprocess.check_output(["arp", "-a"], text=True, timeout=3)
            ips = re.findall(r"(\d+\.\d+\.\d+\.\d+)", out)
            for ip in set(ips):
                if ip.endswith(".255") or ip.startswith("224.") or ip.startswith("239.") or ip.startswith("127."):
                    continue
                try:
                    with socket.create_connection((ip, settings.CAMERA_RTSP_PORT), timeout=0.3):
                        logger.info(f"Auto-discovered CP PLUS camera at {ip}:{settings.CAMERA_RTSP_PORT}")
                        return ip
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"ARP camera scan error: {e}")
        return None

    def test_network_reachability(self, host: str, port: int, timeout: float = 2.0) -> Tuple[bool, str]:
        """Tests TCP socket connectivity to the target host and port."""
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True, f"Port {port} on {host} is OPEN and reachable."
        except socket.timeout:
            return False, f"Connection to {host}:{port} timed out after {timeout}s."
        except ConnectionRefusedError:
            return False, f"Connection refused on {host}:{port} (service down or wrong port)."
        except socket.gaierror:
            return False, f"Address resolution error for host: {host}"
        except Exception as e:
            return False, f"Socket error for {host}:{port}: {str(e)}"

    def discover_stream_profile(self, host: Optional[str] = None, port: Optional[int] = None,
                               username: Optional[str] = None, password: Optional[str] = None) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Sequentially queries known CP PLUS stream paths to discover
        which RTSP URI returns an active H.264/H.265 video stream.
        """
        host = host or settings.CAMERA_IP
        port = port or settings.CAMERA_RTSP_PORT
        username = username or settings.CAMERA_USERNAME
        password = password or settings.CAMERA_PASSWORD

        report: Dict[str, Any] = {
            "target": f"{host}:{port}",
            "tested_profiles": []
        }

        # Check socket reachability first
        is_reachable, socket_msg = self.test_network_reachability(host, port)
        report["port_reachable"] = is_reachable
        report["port_message"] = socket_msg
        if not is_reachable:
            logger.warning(f"RTSP port unreachable: {socket_msg}")
            return None, report

        # Test custom override URL if set
        candidates = []
        if settings.CAMERA_RTSP_OVERRIDE_URL and settings.CAMERA_RTSP_OVERRIDE_URL.strip():
            candidates.append(settings.CAMERA_RTSP_OVERRIDE_URL)

        for path in self.KNOWN_CP_PLUS_PATHS:
            candidates.append(f"rtsp://{username}:{password}@{host}:{port}{path}")

        for test_url in candidates:
            masked = self._mask_url(test_url)
            logger.info(f"Probing CP PLUS stream profile: {masked}")
            
            # Using OpenCV VideoCapture with short timeout
            # Note: OPENCV_FFMPEG_CAPTURE_OPTIONS can be set via env or properties
            cap = cv2.VideoCapture(test_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            success = False
            probe_start = time.time()
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
                    duration = time.time() - probe_start
                    report["tested_profiles"].append({
                        "url": masked,
                        "status": "SUCCESS",
                        "resolution": f"{width}x{height}",
                        "fps": round(fps, 2),
                        "handshake_seconds": round(duration, 3)
                    })
                    cap.release()
                    logger.info(f"Profile found! Resolution: {width}x{height} @ {fps:.1f} FPS")
                    return test_url, report
                else:
                    report["tested_profiles"].append({
                        "url": masked,
                        "status": "CONNECTED_NO_FRAMES"
                    })
            else:
                report["tested_profiles"].append({
                    "url": masked,
                    "status": "CONNECTION_FAILED"
                })
            cap.release()

        return None, report

    def connect(self, rtsp_url: Optional[str] = None) -> bool:
        """
        Establishes connection to the camera stream or launches demo mode stream.
        Spawns background frame reader thread if connection succeeds.
        """
        with self._lock:
            if self._state in (CameraState.CONNECTED, CameraState.STREAMING, CameraState.CONNECTING):
                logger.info(f"Camera is already active in state: {self._state.value}")
                return True
            self._state = CameraState.CONNECTING
            self._stop_requested.clear()

        # If DEMO_MODE is configured, start the bundled demo stream directly
        if settings.DEMO_MODE:
            logger.info("DEMO_MODE=true configured. Initiating real dual-YOLO demo road stream...")
            with self._lock:
                self._state = CameraState.STREAMING
                self._is_demo_active = True
                self._active_rtsp_url = "DEMO_ROAD_STREAM"
                self._last_error = None
            self._thread = threading.Thread(target=self._demo_ingestion_loop, daemon=True, name="Demo_Ingestion")
            self._thread.start()
            return True

        target_url = rtsp_url or settings.get_rtsp_url()
        # If password is missing in standard url, supply configured password or device default
        if "@" in target_url and (":@" in target_url or "rtsp://admin:@" in target_url):
            target_url = target_url.replace("rtsp://admin:@", f"rtsp://admin:{settings.CAMERA_PASSWORD or 'Admin1234'}@")
        masked_url = self._mask_url(target_url)
        logger.info(f"Initiating connection to CP PLUS camera at {masked_url}")

        # Rapid socket reachability probe to prevent FFmpeg blocking on unreachable IP
        host = settings.CAMERA_IP
        port = settings.CAMERA_RTSP_PORT
        is_reachable, reach_msg = self.test_network_reachability(host, port, timeout=1.5)
        if not is_reachable:
            logger.info(f"Camera IP {host}:{port} unreachable. Probing local network for CP PLUS camera...")
            found_ip = self.auto_discover_camera_ip()
            if found_ip:
                logger.info(f"Switching camera IP from {host} to {found_ip}")
                settings.CAMERA_IP = found_ip
                host = found_ip
                stream_path = settings.CAMERA_RTSP_PATH if settings.CAMERA_RTSP_PATH else "/live/channel1"
                pwd = settings.CAMERA_PASSWORD or "Admin1234"
                user = settings.CAMERA_USERNAME or "admin"
                settings.CAMERA_RTSP_OVERRIDE_URL = f"rtsp://{user}:{pwd}@{found_ip}:{port}{stream_path}"
                target_url = settings.CAMERA_RTSP_OVERRIDE_URL
                masked_url = self._mask_url(target_url)
                is_reachable = True
            else:
                logger.info(f"Physical camera offline ({reach_msg}). Falling back to live demo road stream.")
                with self._lock:
                    self._state = CameraState.STREAMING
                    self._is_demo_active = True
                    self._last_error = f"Physical camera offline ({reach_msg}). Serving live AI demo feed."
                self._thread = threading.Thread(target=self._demo_ingestion_loop, daemon=True, name="Demo_Fallback_Ingestion")
                self._thread.start()
                return True

        cap = cv2.VideoCapture(target_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            logger.warning(f"Failed to open RTSP stream at {masked_url}. Falling back to live demo road stream.")
            cap.release()
            with self._lock:
                self._state = CameraState.STREAMING
                self._is_demo_active = True
                self._last_error = f"Failed to open RTSP stream at {masked_url}. Serving live AI demo feed."
            self._thread = threading.Thread(target=self._demo_ingestion_loop, daemon=True, name="Demo_Fallback_Ingestion")
            self._thread.start()
            return True

        ret, frame = cap.read()
        if not ret or frame is None:
            logger.warning("RTSP stream opened but failed to retrieve frame. Falling back to live demo stream.")
            cap.release()
            with self._lock:
                self._state = CameraState.STREAMING
                self._is_demo_active = True
                self._last_error = "Camera opened but failed to read initial frame. Serving live AI demo feed."
            self._thread = threading.Thread(target=self._demo_ingestion_loop, daemon=True, name="Demo_Fallback_Ingestion")
            self._thread.start()
            return True

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0

        with self._lock:
            self._cap = cap
            self._active_rtsp_url = target_url
            self._stream_resolution = (width, height)
            self._stream_fps = fps
            self._last_frame = frame
            self._last_frame_time = time.time()
            self._state = CameraState.STREAMING
            self._is_demo_active = False
            self._last_error = None
            self._reconnect_count = 0

        logger.info(f"Connected to CP PLUS CP-E25A: {width}x{height} @ {fps:.1f} FPS")

        # Start continuous ingestion thread
        self._thread = threading.Thread(target=self._ingestion_loop, daemon=True, name="CP_PLUS_Ingestion")
        self._thread.start()
        return True

    def _demo_ingestion_loop(self):
        """Continuously streams bundled road damage footage at 20 FPS with vehicle motion simulation."""
        logger.info("Demo road stream worker started.")
        total_samples = len(self._demo_frames)
        sample_idx = 0
        step_in_sample = 0
        steps_per_sample = 40  # 2.0 seconds per road sample at 20 FPS

        with self._lock:
            self._stream_resolution = (640, 640)
            self._stream_fps = 20.0
            self._state = CameraState.STREAMING

        while not self._stop_requested.is_set():
            loop_start = time.time()

            if total_samples > 0:
                base_img = self._demo_frames[sample_idx]
                h, w = base_img.shape[:2]

                # Subtle forward perspective zoom (1.0 to 1.12)
                progress = (step_in_sample / float(steps_per_sample))
                zoom = 1.0 + progress * 0.10
                crop_h = int(h / zoom)
                crop_w = int(w / zoom)
                y1 = int((h - crop_h) * 0.7)  # bias towards road tarmac
                x1 = (w - crop_w) // 2
                cropped = base_img[y1 : y1 + crop_h, x1 : x1 + crop_w]
                frame = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

                step_in_sample += 1
                if step_in_sample >= steps_per_sample:
                    step_in_sample = 0
                    sample_idx = (sample_idx + 1) % total_samples
            else:
                frame = self.generate_synthetic_frame("LIVE AI DEMO STREAM (NO SAMPLES LOADED)")

            now = time.time()
            with self._lock:
                self._last_frame = frame
                self._last_frame_time = now
                self._frame_count += 1
                self._state = CameraState.STREAMING

            # 20 FPS timing pacing
            elapsed = time.time() - loop_start
            sleep_needed = (1.0 / 20.0) - elapsed
            if sleep_needed > 0.002:
                time.sleep(sleep_needed)

    def disconnect(self):
        """Cleanly releases video capture and halts ingestion worker."""
        logger.info("Disconnecting camera stream...")
        self._stop_requested.set()

        if self._thread and self._thread.is_alive() and threading.current_thread() != self._thread:
            self._thread.join(timeout=2.0)

        with self._lock:
            if self._cap:
                self._cap.release()
                self._cap = None
            self._state = CameraState.DISCONNECTED
            self._active_rtsp_url = None
            self._last_frame = None
            self._thread = None
            logger.info("Camera stream cleanly disconnected.")

    def switch_to_demo(self):
        """Switches stream to demo highway footage with dual-YOLO inference."""
        self.disconnect()
        self._stop_requested.clear()
        with self._lock:
            self._state = CameraState.STREAMING
            self._is_demo_active = True
            self._active_rtsp_url = "DEMO_ROAD_STREAM"
            self._last_error = None
        self._thread = threading.Thread(target=self._demo_ingestion_loop, daemon=True, name="Demo_Ingestion")
        self._thread.start()
        logger.info("Stream switched to DEMO road footage.")

    def switch_to_live(self) -> bool:
        """Switches stream to physical CP PLUS camera."""
        self.disconnect()
        with self._lock:
            self._is_demo_active = False
        return self.connect()

    def get_latest_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Retrieves the most recent frame captured from the stream."""
        with self._lock:
            if self._last_frame is not None:
                return True, self._last_frame.copy()
            return False, None

    def _ingestion_loop(self):
        """Background worker thread continuously grabbing frames and managing reconnects."""
        logger.info("Camera ingestion thread started.")

        consecutive_failures = 0
        max_failures = 10

        while not self._stop_requested.is_set():
            if self._cap is None or not self._cap.isOpened():
                if not self._handle_reconnection():
                    break
                continue

            ret, frame = self._cap.read()
            if not ret or frame is None:
                consecutive_failures += 1
                logger.warning(f"Frame read dropped ({consecutive_failures}/{max_failures})")
                if consecutive_failures >= max_failures:
                    logger.error("Too many dropped frames. Triggering stream reconnect...")
                    if not self._handle_reconnection():
                        break
                    consecutive_failures = 0
                time.sleep(0.01)
                continue

            consecutive_failures = 0
            now = time.time()

            with self._lock:
                self._last_frame = frame
                self._last_frame_time = now
                self._frame_count += 1
                self._state = CameraState.STREAMING

        logger.info("Camera ingestion thread terminated.")

    def _handle_reconnection(self) -> bool:
        """Executes resilient persistent reconnection routine with network auto-discovery."""
        with self._lock:
            self._state = CameraState.RECONNECTING
            self._reconnect_count += 1
            if self._cap:
                self._cap.release()
                self._cap = None

        backoff = min(settings.CAMERA_RECONNECT_INTERVAL_SECONDS, 5.0)
        time.sleep(backoff)
        if self._stop_requested.is_set():
            return False

        # If current IP is not reachable, probe local network for CP PLUS camera
        host = settings.CAMERA_IP
        port = settings.CAMERA_RTSP_PORT
        is_reachable, _ = self.test_network_reachability(host, port, timeout=0.8)
        if not is_reachable:
            found_ip = self.auto_discover_camera_ip()
            if found_ip:
                logger.info(f"Auto-discovery relocated camera to {found_ip}:{port}")
                settings.CAMERA_IP = found_ip
                stream_path = settings.CAMERA_RTSP_PATH if settings.CAMERA_RTSP_PATH else "/live/channel1"
                pwd = settings.CAMERA_PASSWORD or "Admin1234"
                user = settings.CAMERA_USERNAME or "admin"
                settings.CAMERA_RTSP_OVERRIDE_URL = f"rtsp://{user}:{pwd}@{found_ip}:{port}{stream_path}"
                self._active_rtsp_url = settings.CAMERA_RTSP_OVERRIDE_URL
            else:
                with self._lock:
                    self._last_error = f"Camera offline at {host}:{port}. Waiting for camera power on / Wi-Fi..."
                return True

        target_url = self._active_rtsp_url or settings.get_rtsp_url()
        cap = cv2.VideoCapture(target_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                with self._lock:
                    self._cap = cap
                    self._state = CameraState.STREAMING
                    self._last_frame = frame
                    self._last_frame_time = time.time()
                    self._last_error = None
                    self._reconnect_count = 0
                logger.info("Camera stream successfully re-established!")
                return True

        cap.release()
        return True

    def generate_synthetic_frame(self, text_banner: str = "SYNTHETIC ROAD STREAM (CAMERA SIMULATOR)") -> np.ndarray:
        """
        Generates an animated high-definition road camera simulation pattern.
        Used for development, testing, and CI when the physical CP PLUS camera is offline.
        """
        h, w = 720, 1280
        frame = np.zeros((h, w, 3), dtype=np.uint8)

        # Draw road tarmac (dark gray bottom half)
        frame[h // 2 :, :] = [45, 45, 45]
        # Draw sky/horizon (gradient light blue-gray)
        frame[: h // 2, :] = [180, 170, 160]

        # Draw road perspective lines (lanes)
        cv2.line(frame, (w // 2, h // 2), (50, h), (255, 255, 255), 4)
        cv2.line(frame, (w // 2, h // 2), (w - 50, h), (255, 255, 255), 4)

        # Animated dashed center line
        offset = int((time.time() * 200) % 80)
        for y in range(h // 2 + offset, h, 80):
            scale = (y - h // 2) / (h // 2)
            dash_w = int(6 * scale) + 2
            cv2.line(frame, (w // 2, y), (w // 2, min(y + 35, h)), (0, 220, 255), dash_w)

        # Timestamp and diagnostics overlay
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.rectangle(frame, (20, 20), (w - 20, 90), (0, 0, 0), -1)
        cv2.putText(frame, f"[CP PLUS CP-E25A SIMULATOR] | {timestamp_str}", (35, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 200), 2)
        cv2.putText(frame, text_banner, (35, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        return frame


camera_manager = CameraStreamManager()
