# CP PLUS CP-E25A Camera Setup & RTSP Integration Guide

This guide details how to configure, discover, and integrate the **CP PLUS CP-E25A** (EzyKam Wi-Fi / IP Camera) with the Road Damage and Object Detection System.

---

## 1. Camera Specifications
- **Model**: CP PLUS CP-E25A
- **Resolution**: 1080p Full HD (1920x1080)
- **Sensor**: 2MP CMOS
- **Video Compression**: H.264 / H.265
- **Protocols Supported**: RTSP, ONVIF Profile S, TCP/IP, UDP, DHCP, DNS
- **Default RTSP Port**: 554
- **Default ONVIF Port**: 8000 or 8899

---

## 2. Network Discovery: Finding the Camera's IP Address

When you connect the CP PLUS camera to your local Wi-Fi or Ethernet network:

### Method A: Router DHCP Client List (Fastest)
1. Log into your Wi-Fi router's admin interface (typically `http://192.168.1.1` or `http://192.168.0.1`).
2. Navigate to **Connected Devices** / **DHCP Client Table**.
3. Locate the device named `CP-PLUS`, `EzyKam`, or starting with the MAC vendor `Dahua / CP PLUS`.
4. Note the assigned IP address (e.g., `192.168.1.145`).

### Method B: ONVIF Device Manager (Windows Tool)
1. Download and open **ONVIF Device Manager (ODM)** (open-source tool).
2. The tool scans your local subnet and lists all ONVIF cameras automatically.
3. Enter your camera credentials in ODM to view stream profiles and exact RTSP URLs.

### Method C: CP PLUS ConfigTool / EzyKam Mobile App
1. Use the **CP PLUS ConfigTool** on Windows to search the local network.
2. In the camera settings, it is **strongly recommended** to switch from dynamic DHCP to a **Static IP** (or set a DHCP reservation in your router) so the camera IP never changes upon reboot.

---

## 3. RTSP URL Formats for CP PLUS CP-E25A

The system automatically generates the RTSP stream URL using the following templates:

### 1. Main Stream (High Resolution - 1080p @ 25/30 FPS)
Best for high-precision crack detection and saving evidence snapshots:
```text
rtsp://<username>:<password>@<ip_address>:554/cam/realmonitor?channel=1&subtype=0
```

### 2. Sub Stream (Standard Definition - 360p / 480p @ 25 FPS)
Best for high-throughput, low-latency AI inference on CPU:
```text
rtsp://<username>:<password>@<ip_address>:554/cam/realmonitor?channel=1&subtype=1
```

### 3. Alternative Firmware Profile
For certain OEM firmware versions:
```text
rtsp://<username>:<password>@<ip_address>:554/live/ch0
```

---

## 4. Configuring the Project `.env`

Edit the `.env` file in the project root:

```env
CAMERA_NAME="CP-PLUS-CP-E25A"
CAMERA_IP=192.168.1.145          # Replace with your camera's actual local IP
CAMERA_RTSP_PORT=554             # Default RTSP port
CAMERA_ONVIF_PORT=8000           # Default ONVIF port
CAMERA_USERNAME=admin            # Camera username
CAMERA_PASSWORD=YourPassword     # Camera password
CAMERA_STREAM_SUBTYPE=0          # 0 for Main Stream, 1 for Sub Stream
```

---

## 5. Security & Isolation Best Practices

1. **Change Default Credentials Immediately**: Never deploy with `admin/admin`.
2. **Isolate on an IoT VLAN**: If possible, place surveillance cameras on a dedicated guest or IoT network segment.
3. **Do NOT Port Forward Port 554**: Never expose your camera directly to the public internet by forwarding port 554 in your home router. The AI backend securely connects to the camera locally and handles public access via encrypted tunnels (Phase 13).

---

## 6. Testing Camera Connectivity

Run the automated diagnostic tool:
```powershell
.\venv\Scripts\python.exe scripts\test_camera.py
```
This tests TCP ports, discovers valid stream profiles, and captures a test frame to `backend/storage/snapshots/camera_test_snapshot.jpg`.
