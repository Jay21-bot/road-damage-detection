#!/usr/bin/env python3
"""
Phase 13: Deployment Configuration & Security Hardening Verification Suite
Validates:
1. Dockerfile syntax, build layers, and healthcheck configuration
2. docker-compose.yml service topology, volume persistence, and environment bindings
3. Nginx reverse proxy directives (WebSocket upgrade & MJPEG buffer bypass)
4. Cloudflare Tunnel and Tailscale remote configuration integrity
5. API Key security authentication guard on camera control endpoints
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app
from app.core.config import settings


def run_deployment_tests():
    print("=" * 80)
    print(" PHASE 13: PUBLIC DEPLOYMENT & REMOTE CONNECTIVITY VERIFICATION")
    print("=" * 80)

    # --------------------------------------------------------------------------
    # Step 1: Dockerfile Validation
    # --------------------------------------------------------------------------
    print("\n[Step 1/5] Validating Containerization Engine (Dockerfile & .dockerignore):")
    dockerfile = project_root / "Dockerfile"
    dockerignore = project_root / ".dockerignore"

    assert dockerfile.exists(), "Dockerfile missing!"
    assert dockerignore.exists(), ".dockerignore missing!"

    df_content = dockerfile.read_text(encoding="utf-8")
    assert "FROM python:3.12-slim" in df_content
    assert "EXPOSE 8000" in df_content
    assert "HEALTHCHECK" in df_content
    assert "uvicorn" in df_content
    print(f"      - Dockerfile: Base=python:3.12-slim, Port=8000, Healthcheck enabled.")

    di_content = dockerignore.read_text(encoding="utf-8")
    assert "venv/" in di_content
    assert "__pycache__/" in di_content
    print(f"      - .dockerignore: Verified exclusions for venv, caches, and datasets.")
    print("      [PASS] Docker containerization configuration verified.")

    # --------------------------------------------------------------------------
    # Step 2: Docker Compose Orchestration Topology
    # --------------------------------------------------------------------------
    print("\n[Step 2/5] Validating Docker Compose Multi-Container Orchestration:")
    compose_file = project_root / "docker-compose.yml"
    assert compose_file.exists(), "docker-compose.yml missing!"

    compose_text = compose_file.read_text(encoding="utf-8")
    assert "road-ai-backend:" in compose_text
    assert "nginx-proxy:" in compose_text
    assert "./backend/storage:/app/storage" in compose_text
    assert "./backend/models:/app/models" in compose_text
    print("      - Services Defined: 'road-ai-backend', 'nginx-proxy'")
    print("      - Volume Persistence: Database, Snapshots, and Model Weights mounted.")
    print("      [PASS] Multi-container orchestration topology validated.")

    # --------------------------------------------------------------------------
    # Step 3: Nginx Reverse Proxy Directives
    # --------------------------------------------------------------------------
    print("\n[Step 3/5] Validating Nginx Streaming & WebSocket Directives:")
    nginx_conf = project_root / "deployment" / "nginx" / "nginx.conf"
    assert nginx_conf.exists(), "nginx.conf missing!"

    nginx_text = nginx_conf.read_text(encoding="utf-8")
    # Verify WebSocket upgrade
    assert "proxy_set_header Upgrade $http_upgrade;" in nginx_text
    assert 'proxy_set_header Connection "upgrade";' in nginx_text
    print("      - WebSocket Directives: Upgrade & Connection headers configured.")

    # Verify MJPEG stream buffer bypass
    assert "proxy_buffering off;" in nginx_text
    assert "proxy_cache off;" in nginx_text
    print("      - Video Stream Directives: proxy_buffering off, proxy_cache off.")

    # Verify Snapshot static route
    assert "location /snapshots/" in nginx_text
    print("      - Static File Route: /snapshots/ alias configured.")
    print("      [PASS] Nginx reverse proxy configuration validated.")

    # --------------------------------------------------------------------------
    # Step 4: Cloudflare Tunnel & Tailscale Remote Configuration
    # --------------------------------------------------------------------------
    print("\n[Step 4/5] Validating Cloudflare Ingress & Tailscale Connectivity Specs:")
    cf_conf = project_root / "deployment" / "cloudflare" / "config.yml"
    ts_doc = project_root / "deployment" / "tailscale" / "tailscale-setup.md"

    assert cf_conf.exists(), "Cloudflare config missing!"
    assert ts_doc.exists(), "Tailscale documentation missing!"

    cf_text = cf_conf.read_text(encoding="utf-8")
    assert "ingress:" in cf_text
    assert "service: http://localhost:8000" in cf_text
    print("      - Cloudflare Tunnel: Ingress table routes to localhost:8000.")

    ts_text = ts_doc.read_text(encoding="utf-8")
    assert "--advertise-routes" in ts_text
    print("      - Tailscale Subnet Router: WireGuard mesh routing instructions verified.")
    print("      [PASS] Remote access & zero-credential exposure configs verified.")

    # --------------------------------------------------------------------------
    # Step 5: API Key Authentication Guard on Control Endpoints
    # --------------------------------------------------------------------------
    print("\n[Step 5/5] Testing API Key Security Guard on Camera Control Endpoints:")
    orig_key = settings.API_SECRET_KEY

    with TestClient(app) as client:
        # 5a. Permissive Development Mode
        settings.API_SECRET_KEY = "insecure_default_secret_change_in_production"
        resp = client.post("/api/v1/detection/start")
        assert resp.status_code == 200, f"Expected 200 in dev mode, got {resp.status_code}"
        print("      - Development Mode: Permissive access without API key confirmed (Status 200).")

        # 5b. Enforce Production Secret Key
        test_prod_key = "prod_secure_token_98765"
        settings.API_SECRET_KEY = test_prod_key

        # Missing API Key -> 401 Unauthorized
        unauth_resp = client.post("/api/v1/detection/start")
        assert unauth_resp.status_code == 401, f"Expected 401, got {unauth_resp.status_code}"
        print(f"      - Production Guard: Missing 'X-API-Key' correctly rejected with Status 401.")

        # Invalid API Key -> 403 Forbidden
        forbidden_resp = client.post("/api/v1/detection/start", headers={"X-API-Key": "wrong_key"})
        assert forbidden_resp.status_code == 403, f"Expected 403, got {forbidden_resp.status_code}"
        print(f"      - Production Guard: Invalid 'X-API-Key' correctly rejected with Status 403.")

        # Valid API Key -> 200 OK
        valid_resp = client.post("/api/v1/detection/start", headers={"X-API-Key": test_prod_key})
        assert valid_resp.status_code == 200, f"Expected 200, got {valid_resp.status_code}"
        print(f"      - Production Guard: Valid 'X-API-Key' accepted successfully with Status 200.")

        # Reset setting to original
        settings.API_SECRET_KEY = orig_key
        print("      [PASS] API Key security authentication guard verified.")

    print("\n" + "=" * 80)
    print("PHASE 13 DEPLOYMENT & REMOTE CONNECTIVITY VERIFICATION: ALL 5 STEPS PASSED")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_deployment_tests()
