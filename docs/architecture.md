# AI-Based Road Damage Detection & Real-Time Object Recognition System
## System Architecture & Technical Specification (Phase 1)

---

### 1. Executive Summary & System Vision
The **AI-Based Road Damage Detection and Real-Time Object Recognition System** is an end-to-end computer vision and IoT analytics platform designed to:
- Intercept live video from industrial/surveillance IP cameras (specifically the **CP PLUS CP-E25A**).
- Decode and preprocess real-time RTSP streams via a resilient OpenCV multi-threaded ingestion pipeline.
- Concurrently execute dual Ultralytics YOLO models:
  1. **Road Damage Model**: Custom-trained on standardized road damage datasets (e.g., RDD2020 / RDD2022) to detect structural anomalies (potholes, longitudinal cracks, transverse cracks, alligator cracking).
  2. **General Object Model**: Pretrained YOLO (e.g., YOLOv8n/s or YOLO11n/s) to track road-dwelling objects (vehicles, trucks, buses, motorcycles, pedestrians, animals, traffic signals).
- Broadcast low-latency visual feeds and structured telemetry via WebSockets and REST APIs to a modern React/Tailwind web dashboard.
- Persist detections, telemetry, metrics, and incident snapshots in an extensible SQLite database (architected for seamless PostgreSQL migration).
- Provide secure public access through cloud-native reverse proxies and network tunneling (Tailscale / Cloudflare Tunnel) without exposing local camera credentials or unencrypted RTSP streams to the public internet.

---

### 2. High-Level Architectural Topology

```mermaid
flowchart TD
    subgraph Edge_LAN["Local Camera Network (Edge LAN)"]
        CAM["CP PLUS CP-E25A IP Camera\n(1080p / 30fps RTSP & ONVIF)"]
        ROUTER["Local Gateway / Router"]
        CAM -->|RTSP:554 / ONVIF:80/8899| ROUTER
    end

    subgraph Secure_Tunnel["Secure Ingress / Tunneling"]
        TUNNEL["Secure Tunnel / Reverse Proxy\n(Tailscale / WireGuard / Cloudflare Tunnel)"]
        ROUTER -.->|Encrypted Pipe| TUNNEL
    end

    subgraph Backend_Server["Python FastAPI Application Server (GPU / CPU)"]
        subgraph Ingestion["Video Ingestion Layer"]
            CAP["RTSP Stream Thread\n(OpenCV VideoCapture / FFmpeg)"]
            BUF["Circular Frame Ring Buffer\n(Thread-Safe Queue, Frame Dropping)"]
            CAP --> BUF
        end

        subgraph Inference_Engine["AI Inference Pipeline (Ultralytics YOLO)"]
            PREPROC["Preprocessor\n(Resize, Normalize, Letterbox)"]
            YOLO_ROAD["Model A: Custom Road Damage\n(Potholes, Cracks D00/D10/D20/D40)"]
            YOLO_OBJ["Model B: General Object Detection\n(Vehicles, Pedestrians, Signs)"]
            POSTPROC["Postprocessor & Filter\n(NMS, Bounding Box Fusion, Deduplication)"]
            
            BUF --> PREPROC
            PREPROC --> YOLO_ROAD
            PREPROC --> YOLO_OBJ
            YOLO_ROAD --> POSTPROC
            YOLO_OBJ --> POSTPROC
        end

        subgraph Services["Core Application Services"]
            CAM_SVC["Camera Manager & Health Check"]
            DET_SVC["Detection & Snapshot Service"]
            STAT_SVC["Analytics & Aggregation Service"]
            AUTH_SVC["Security & Auth Handler"]
        end

        subgraph Data_Storage["Persistence Layer"]
            SQLITE[("SQLite Database\n(SQLAlchemy ORM + Alembic)")]
            FS_STORAGE[("Snapshot File System\n(/storage/snapshots)")]
        end

        POSTPROC --> DET_SVC
        DET_SVC --> SQLITE
        DET_SVC --> FS_STORAGE
    end

    subgraph Web_Tier["Web & Streaming Layer"]
        WS_MGR["FastAPI WebSocket Manager\n(/ws/detections)"]
        REST_API["FastAPI REST Endpoints\n(/camera, /detections, /statistics)"]
        STREAM_EP["MJPEG / Annotated Stream Endpoint\n(/camera/stream)"]
        
        POSTPROC --> WS_MGR
        POSTPROC --> STREAM_EP
        CAM_SVC --> REST_API
        STAT_SVC --> REST_API
        DET_SVC --> REST_API
    end

    subgraph Frontend["Frontend Dashboard (Bolt.new / React / Vite / Tailwind)"]
        UI_DASH["Executive Dashboard"]
        UI_LIVE["Live Video & Canvas Overlay"]
        UI_DAMAGE["Road Damage Gallery & Details"]
        UI_OBJ["Object Analytics & Filtering"]
        UI_HIST["Searchable Detection Logs"]
        UI_SETTINGS["Configuration & Diagnostics"]
    end

    TUNNEL --> CAP
    WS_MGR <==>|WSS Real-Time Telemetry| Frontend
    REST_API <==>|HTTPS JSON Data| Frontend
    STREAM_EP ==>|Video Feed| UI_LIVE
```

---

### 3. Hardware & Camera Specifications (CP PLUS CP-E25A)

| Parameter | Specification | Integration Strategy |
| :--- | :--- | :--- |
| **Model** | CP PLUS CP-E25A EzyKam / Wi-Fi IP Camera | 2MP Full HD IP Camera |
| **Video Resolution** | 1080p (1920x1080) @ 20-30 fps | Scaled to 640x640 / 720p for AI inference to conserve VRAM |
| **Compression** | H.264 / H.265 | Handled transparently by FFmpeg backend in OpenCV |
| **Streaming Protocol** | RTSP (Real-Time Streaming Protocol) | Default port 554; path configured dynamically via `.env` |
| **Management Protocol** | ONVIF Profile S | Discovery on port 80 / 8899 / 8000 for profile retrieval |
| **Network Interfaces** | Wi-Fi (2.4 GHz) / RJ45 Ethernet | Requires static IP or DHCP reservation on local gateway |
| **Credential Security** | Username & Password | Never passed to client; held server-side in secure vault / `.env` |

#### Standard RTSP URL Patterns for CP PLUS:
1. `rtsp://<username>:<password>@<ip_address>:<port>/cam/realmonitor?channel=1&subtype=0` (Main Stream - High Res)
2. `rtsp://<username>:<password>@<ip_address>:<port>/cam/realmonitor?channel=1&subtype=1` (Sub Stream - Low Res / Detection Friendly)
3. `rtsp://<username>:<password>@<ip_address>:<port>/live/ch0` (Alternative firmware)
4. `rtsp://<username>:<password>@<ip_address>:<port>/onvif1` (Standard ONVIF mapping)

---

### 4. Technology Stack Selection & Rationales

| Layer | Technology | Version | Selection Justification |
| :--- | :--- | :--- | :--- |
| **AI Framework** | Ultralytics YOLO | v8 / v11 (PyTorch) | State-of-the-art real-time speed, high accuracy on edge GPUs/CPUs, flexible export options (ONNX, TensorRT). |
| **Computer Vision** | OpenCV (`opencv-python-headless`) | >= 4.9.0 | Low-latency stream decoding, image transformations, color space conversions, bounding box overlays. |
| **Backend Framework** | FastAPI + Uvicorn | >= 0.110.0 | High-performance asynchronous execution, native WebSocket support, automatic OpenAPI/Swagger documentation, Pydantic validation. |
| **ORM / Persistence** | SQLAlchemy + Alembic + SQLite | 2.0+ | Zero-configuration local database with clean abstractions, allowing one-click transition to PostgreSQL in production. |
| **Frontend Framework** | React + TypeScript + Vite | React 18+ | Lightning-fast HMR, strict type safety, modular component tree, excellent ecosystem compatibility with Bolt.new. |
| **Styling & UI** | Tailwind CSS + Lucide Icons | Latest | Modern dark-mode surveillance UI, zero runtime CSS overhead, accessible responsive layouts. |
| **Streaming Protocol** | WebSocket + MJPEG / Base64 | RFC 6455 | High-frequency telemetry (30 fps metadata) paired with optimized frame streaming without complex WebRTC gateway overhead. |
| **Deployment / Proxy** | Cloudflare Tunnel / Tailscale | Latest | Exposes private backend to public internet over HTTPS/WSS without opening router ports or exposing camera to attackers. |

---

### 5. AI Detection Architecture: Dual-Model Pipeline

```mermaid
sequenceDiagram
    participant Camera as CP PLUS Camera
    participant Ingest as Frame Reader Thread
    participant Queue as Ring Buffer (Queue)
    participant Worker as Inference Worker
    participant ModelA as Road Damage Model
    participant ModelB as General Object Model
    participant Broadcast as WebSocket & DB

    Camera->>Ingest: RTSP Stream (H.264/H.265)
    Ingest->>Queue: Push newest frame (Drop stale frames)
    Worker->>Queue: Pop latest frame
    par Run Road Damage Model
        Worker->>ModelA: Predict(frame, conf=0.35, imgsz=640)
        ModelA-->>Worker: [Pothole, Transverse Crack, Alligator Crack]
    and Run General Object Model
        Worker->>ModelB: Predict(frame, conf=0.45, imgsz=640)
        ModelB-->>Worker: [Car, Pedestrian, Truck]
    end
    Worker->>Worker: Fuse Predictions + Annotate Overlay
    Worker->>Broadcast: Emit Telemetry Event & Store High-Confidence Incidents
```

#### Supported Damage Classes (Target Dataset Standard - RDD2020 / RDD2022):
- **D00**: Longitudinal Crack (along the direction of traffic)
- **D10**: Transverse Crack (perpendicular to traffic direction)
- **D20**: Alligator Crack / Fatigue Cracking (mesh/net pattern)
- **D40**: Pothole / Road Pit / Broken Surface
- **D43 / D44**: Crosswalk blur, lane line blur (optional surface wear)

#### Supported General Object Classes (COCO 80 Standard):
- Vehicles: `car`, `motorcycle`, `bus`, `truck`, `bicycle`
- Vulnerable Road Users: `person`, `dog`, `cat`
- Infrastructure: `traffic light`, `stop sign`

---

### 6. Data Model & Entity Relationship (ER) Design

```mermaid
erDiagram
    CAMERA ||--o{ DETECTION_SESSION : hosts
    DETECTION_SESSION ||--o{ DETECTION_EVENT : generates
    DETECTION_EVENT ||--o{ BOUNDING_BOX : contains

    CAMERA {
        string id PK
        string name
        string ip_address
        int rtsp_port
        int onvif_port
        string stream_path
        boolean is_active
        datetime last_seen
    }

    DETECTION_SESSION {
        string id PK
        string camera_id FK
        datetime started_at
        datetime stopped_at
        int total_frames_processed
        float average_fps
    }

    DETECTION_EVENT {
        string id PK
        string session_id FK
        datetime timestamp
        string category "road_damage | general_object"
        string primary_class
        float confidence
        string snapshot_path
        boolean flagged_for_review
    }

    BOUNDING_BOX {
        string id PK
        string event_id FK
        string class_name
        float confidence
        float x_min
        float y_min
        float x_max
        float y_max
    }
```

---

### 7. Security, Networking & Public Accessibility Strategy

1. **Zero Credential Exposure**:
   - The React frontend receives **zero** camera IP addresses, passwords, or raw RTSP links.
   - All camera communication is negotiated server-side by FastAPI.
2. **Network Isolation & Secure Remote Tunneling**:
   - Camera sits in an isolated IoT VLAN on the edge network.
   - The backend runs on a host with access to the IoT VLAN and creates an outbound encrypted tunnel (Cloudflare Tunnel `cloudflared` or Tailscale Funnel) to a public domain (e.g., `https://road-ai.yourdomain.com`).
   - No inbound router ports (Port 554, 80, 8000) are opened to the public internet.
3. **Authentication & Authorization**:
   - API key or JWT Bearer authentication on sensitive endpoints (`/camera/connect`, `/detection/start`).
   - Rate limiting on control endpoints to prevent camera DoS or buffer exhaustion.

---

### 8. Phase Breakdown & Execution Roadmap

- **Phase 1 (Current)**: Architecture, Specifications, and Technical Blueprint.
- **Phase 2**: Python Environment Setup, Dependencies & Project Directory Scaffolding.
- **Phase 3**: CP PLUS Camera RTSP/ONVIF Connectivity, Diagnostics & Reconnect Engine.
- **Phase 4**: Multi-Threaded Real-Time Video Processing & Latency Control Pipeline.
- **Phase 5**: YOLO General Object Detection Integration (COCO Classes).
- **Phase 6**: Custom Road Damage Model Preparation & Training Pipeline (RDD Dataset).
- **Phase 7**: Simultaneous Dual-Inference Engine & Telemetry Fusion.
- **Phase 8**: FastAPI REST API Backend with Modular Routers.
- **Phase 9**: Real-Time WebSocket Streaming Engine for Low-Latency Telemetry.
- **Phase 10**: Bolt.new Frontend Dashboard (React + TypeScript + Tailwind CSS).
- **Phase 11**: Frontend-Backend End-to-End Integration & Real-Time Canvas Rendering.
- **Phase 12**: Database Persistence, Snapshot Storage, and Searchable History.
- **Phase 13**: Remote Camera Tunneling & Production Deployment Setup.
- **Phase 14**: System Hardening, Benchmarking, Open-Source Documentation & GitHub Release.
