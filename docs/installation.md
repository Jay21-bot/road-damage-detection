# Installation & Environment Setup Guide

Comprehensive setup and deployment instructions for the **AI-Based Road Damage Detection and Real-Time Object Recognition System**.

---

## 1. System Requirements

### Hardware Sizing
- **CPU**: Multi-core processor (Intel Core i5/i7/i9 8th Gen+, AMD Ryzen 5/7/9, or Apple Silicon via ARM build).
- **RAM**: Minimum 8 GB (16 GB recommended for multi-stream deployments).
- **GPU (Optional for 60+ FPS)**: NVIDIA GPU with CUDA 11.8 or 12.1+ support (RTX 3060+, RTX 4000 series, or NVIDIA Jetson Orin/Xavier).
- **Camera Target**: CP PLUS CP-E25A 1080p RTSP IP Camera (or any ONVIF/RTSP compliant camera).

### Operating Systems Supported
- **Windows**: Windows 10 / Windows 11 (PowerShell 7+ recommended)
- **Linux**: Ubuntu 22.04 LTS / 24.04 LTS, Debian 12, CentOS/RHEL 9
- **Docker**: Linux Container Runtime with NVIDIA Container Toolkit (for GPU passthrough)

---

## 2. Windows 11 Setup Guide

### Step 2.1: Python 3.12 Installation
Install Python 3.12 from [python.org](https://www.python.org/downloads/) ensuring **"Add Python to PATH"** is checked.

### Step 2.2: Clone Repository & Create Virtual Environment
```powershell
git clone https://github.com/your-username/road-damage-detection.git
cd "road-damage-detection"

# Provision Virtual Environment
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 2.3: Install Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

### Step 2.4: Configure Environment Variables
```powershell
Copy-Item .env.example .env
# Edit .env with your camera credentials and desired configuration
```

### Step 2.5: Verify Environment
```powershell
python scripts/verify_env.py
```

---

## 3. Ubuntu / Debian Linux Setup

```bash
# 1. Install system prerequisites and OpenCV libraries
sudo apt-get update && sudo apt-get install -y \
    python3.12 python3.12-venv python3-pip \
    libgl1 libglib2.0-0 libgomp1 ffmpeg curl git

# 2. Clone repository
git clone https://github.com/your-username/road-damage-detection.git
cd road-damage-detection

# 3. Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# 4. Install dependencies
pip install --upgrade pip
pip install -r backend/requirements.txt

# 5. Verify system
python scripts/verify_env.py
```

---

## 4. CP PLUS CP-E25A Network Configuration

1. Connect the CP PLUS camera to your PoE switch or local 12V DC power adapter.
2. Default Camera IP: `192.168.1.100` (Subnet mask `255.255.255.0`).
3. Set your workstation's secondary IP to `192.168.1.50` to reach the camera's web configuration portal.
4. Verify standard CP PLUS RTSP URL format:
   ```
   rtsp://<username>:<password>@<ip_address>:554/cam/realmonitor?channel=1&subtype=0
   ```
   - `subtype=0`: High-Resolution Main Stream (1080p, 25/30 FPS)
   - `subtype=1`: Low-Resolution Sub Stream (D1/VGA, lower bandwidth)
5. Test connectivity using our built-in probe:
   ```powershell
   python scripts/test_camera.py
   ```

---

## 5. Running the Application

### Method A: Local Development Server
```powershell
# Start FastAPI backend (includes auto-mounted React dashboard at http://localhost:8000)
.\venv\Scripts\python.exe backend/main.py
```

### Method B: Docker Compose (Production)
```bash
docker compose up -d --build
```
Access the tactical surveillance console at:
- **Web Dashboard**: `http://localhost:8000/`
- **Swagger API Docs**: `http://localhost:8000/docs`
- **Live MJPEG Stream**: `http://localhost:8000/api/v1/camera/stream`
- **WebSocket Telemetry**: `ws://localhost:8000/ws/detections`
