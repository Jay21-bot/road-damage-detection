# Production Deployment & Remote Camera Connectivity Guide

This document details the production deployment, remote camera ingestion, and public hosting architecture for the **AI-Based Road Damage Detection and Real-Time Object Recognition System**.

---

## 1. Architectural Topologies

The system supports three primary deployment topologies:

### A. Edge-Native Appliance (Recommended for Low Latency)
- **Host**: Local Mini PC, Industrial Edge Server, or Workstation (Intel Core i5/i7, AMD Ryzen, NVIDIA Jetson).
- **Network**: Direct physical connection to the camera's local IoT subnet (`192.168.1.0/24`).
- **Remote Access**: Cloudflare Tunnel or Tailscale Funnel exposes the FastAPI web dashboard without inbound router ports.

### B. Cloud VPS with Tailscale Subnet Routing
- **Host**: Cloud GPU instance (AWS EC2 g4dn, GCP T4, RunPod, Hetzner).
- **Network**: Connects to the local camera network over an encrypted WireGuard mesh tunnel managed by Tailscale.
- **Benefits**: Centralized processing for multiple remote camera streams across distributed roadways.

### C. Containerized Docker / Kubernetes Swarm
- **Host**: Linux / Windows container runtime with GPU passthrough (`nvidia-container-toolkit`).
- **Orchestration**: Docker Compose or Kubernetes StatefulSets for automated self-healing.

---

## 2. Docker Quickstart

### Prerequisites
- Docker Engine $\ge 24.0$
- Docker Compose $\ge 2.20$

### Deployment Commands

```bash
# 1. Clone repository & configure environment variables
cp .env.example .env
nano .env

# 2. Build and run containers in detached mode
docker compose up -d --build

# 3. Check runtime container logs
docker compose logs -f road-ai-backend

# 4. Verify system health
curl -f http://localhost:8000/health
```

### Volume Persistence
- `backend/storage/`: Stores SQLite relational database (`road_detection.db`) and JPEG incident snapshots (`/storage/snapshots/`).
- `backend/models/`: Holds dual YOLO neural network weights (`road_damage_best.pt`, `yolov8n.pt`).

---

## 3. Zero-Credential Exposure & Security Strategy

1. **Zero Credential Transmission**:
   - The React / Bolt.new frontend receives **no raw camera RTSP URLs or camera passwords**.
   - All RTSP decoding occurs server-side via OpenCV with internal non-blocking queues.
2. **API Key Protected Controls**:
   - Camera reconfiguration (`POST /api/v1/camera/connect`) and AI inference toggles (`POST /api/v1/detection/start`) require the `X-API-Key` header when `API_SECRET_KEY` is set in `.env`.
3. **Network Isolation**:
   - Keep the CP PLUS camera on an isolated IoT VLAN without direct outbound internet access.
   - Only the AI server communicates with the camera's RTSP port 554 and ONVIF port 8000.

---

## 4. Public Access via Cloudflare Tunnel

Cloudflare Tunnel (`cloudflared`) securely connects your local edge server to Cloudflare's global edge network without opening any firewall ports or managing dynamic DNS.

### Setup Steps

```bash
# 1. Install cloudflared
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# 2. Authenticate tunnel
cloudflared tunnel login

# 3. Create named tunnel
cloudflared tunnel create road-ai-surveillance

# 4. Apply configuration file
sudo cp deployment/cloudflare/config.yml /etc/cloudflared/config.yml
# Update tunnel UUID and hostname in /etc/cloudflared/config.yml

# 5. Route DNS traffic to the tunnel
cloudflared tunnel route dns road-ai-surveillance road-ai.yourdomain.com

# 6. Run tunnel as a continuous system service
sudo cloudflared service install
sudo systemctl start cloudflared
```

Once running, your surveillance dashboard is live at `https://road-ai.yourdomain.com` with automatic Cloudflare SSL/TLS termination and DDoS mitigation.

---

## 5. Nginx Reverse Proxy Configuration

When hosting behind Nginx, two critical directives are required:
1. **WebSocket Protocol Upgrade**: For `/ws/detections` real-time telemetry streaming:
   ```nginx
   proxy_http_version 1.1;
   proxy_set_header Upgrade $http_upgrade;
   proxy_set_header Connection "upgrade";
   ```
2. **Buffer Bypass for Video**: For `/api/v1/camera/stream` multipart MJPEG streaming:
   ```nginx
   proxy_buffering off;
   proxy_cache off;
   chunked_transfer_encoding on;
   ```

A complete, battle-tested configuration is provided in [deployment/nginx/nginx.conf](file:///c:/Ai%20road%20detection%20system/deployment/nginx/nginx.conf).

---

## 6. System Resource Sizing

| Metric | CPU-Only Mode (Development) | GPU-Accelerated Mode (Production) |
| :--- | :--- | :--- |
| **Processor** | 6+ Core CPU (Ryzen 5/7, Intel i5/i7) | 4+ Core CPU + NVIDIA GPU (GTX 1660 / RTX 3050+) |
| **RAM** | 8 GB minimum (16 GB recommended) | 16 GB system RAM + 4 GB VRAM |
| **Throughput** | 15 – 20 FPS (Frame Skip = 2) | 30 – 60 FPS (Continuous real-time) |
| **Inference Latency** | ~35 – 55 ms per batch | ~8 – 15 ms per batch |
| **Storage** | 20 GB SSD (Database + Snapshots) | 50 GB NVMe SSD |
