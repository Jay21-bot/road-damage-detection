# Secure Remote Camera Connectivity via Tailscale

This guide outlines how to connect remote or edge **CP PLUS CP-E25A** cameras to the AI Road Detection backend without port forwarding or exposing camera credentials to the public internet.

---

### Architecture Overview

```
[ CP PLUS CP-E25A ] (Local IP: 192.168.1.100:554)
         │
[ Edge Subnet Router ] (e.g. Raspberry Pi / Mini PC on Local LAN)
         │  (Encrypted WireGuard Mesh)
    [ Tailscale Tailnet ]
         │
[ Backend AI Server ] (Cloud VPS / Central Server)
         │
    FastAPI + YOLO Engine ingesting rtsp://admin:***@192.168.1.100:554/...
```

---

### Step 1: Install Tailscale on the Local Edge Device

Install Tailscale on any computer or single-board computer connected to the same LAN as the CP PLUS camera:

```bash
# Debian / Ubuntu / Raspberry Pi OS
curl -fsSL https://tailscale.com/install.sh | sh
```

### Step 2: Advertise Local Camera Subnet

Run Tailscale advertising the camera's local subnet (e.g., `192.168.1.0/24`):

```bash
sudo tailscale up --advertise-routes=192.168.1.0/24 --accept-routes
```

In the [Tailscale Admin Console](https://login.tailscale.com/admin/machines):
1. Navigate to the edge machine.
2. Under **Edit route settings**, approve `192.168.1.0/24`.

### Step 3: Connect Cloud / Remote Backend Server

On your cloud or centralized AI server, join the same Tailnet:

```bash
sudo tailscale up --accept-routes
```

Verify camera reachability directly from the cloud server:

```bash
ping 192.168.1.100
nc -zv 192.168.1.100 554
```

### Step 4: Configure Backend Environment

In `.env`:

```env
CAMERA_IP=192.168.1.100
CAMERA_RTSP_PORT=554
CAMERA_USERNAME=admin
CAMERA_PASSWORD=your_secure_password
```

The backend server can now securely pull the RTSP stream over the encrypted Tailnet tunnel without opening any router ports!
