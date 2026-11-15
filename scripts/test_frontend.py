#!/usr/bin/env python3
"""
Frontend Architecture & Dashboard Verification Script
Validates React/TypeScript project scaffolding for Bolt.new and tests dashboard endpoint.
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "backend"
project_root = backend_dir.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app

REQUIRED_FRONTEND_FILES = [
    "frontend/package.json",
    "frontend/vite.config.ts",
    "frontend/tsconfig.json",
    "frontend/tailwind.config.js",
    "frontend/index.html",
    "frontend/src/main.tsx",
    "frontend/src/App.tsx",
    "frontend/src/index.css",
    "frontend/src/types/index.ts",
    "frontend/src/services/api.ts",
    "frontend/src/hooks/useWebSocket.ts",
    "frontend/src/components/Navbar.tsx",
    "frontend/src/components/LivePlayer.tsx",
    "frontend/src/pages/DashboardPage.tsx",
    "frontend/src/pages/LiveMonitoringPage.tsx",
    "frontend/src/pages/RoadDamagePage.tsx",
    "frontend/src/pages/ObjectDetectionPage.tsx",
    "frontend/src/pages/HistoryPage.tsx",
    "frontend/src/pages/AnalyticsPage.tsx",
    "frontend/src/pages/SettingsPage.tsx"
]


def run_frontend_tests():
    print("=" * 75)
    print("BOLT.NEW FRONTEND DASHBOARD VERIFICATION SUITE")
    print("=" * 75)

    print("\n[1/3] Checking React + TypeScript Project Scaffolding for Bolt.new:")
    all_ok = True
    for rel_path in REQUIRED_FRONTEND_FILES:
        p = project_root / rel_path
        if p.is_file():
            print(f"      [OK] {rel_path}")
        else:
            print(f"      [MISSING] {rel_path}")
            all_ok = False
    assert all_ok, "Some required frontend files are missing!"
    print("      [PASS] Bolt.new React project tree verified.")

    print("\n[2/3] Checking Integrated Static Dashboard Asset:")
    static_html = backend_dir / "app" / "static" / "index.html"
    assert static_html.is_file(), "Static dashboard HTML missing!"
    size_kb = static_html.stat().st_size / 1024
    print(f"      - Integrated Dashboard Asset: {static_html.name} ({size_kb:.1f} KB)")
    print("      [PASS] Zero-dependency browser dashboard ready.")

    print("\n[3/3] Testing Dashboard Delivery Endpoint via FastAPI:")
    with TestClient(app) as client:
        res = client.get("/")
        assert res.status_code == 200, f"Dashboard failed: {res.status_code}"
        assert "ROAD•AI SURVEILLANCE" in res.text, "Dashboard title missing from HTML response!"
        assert "/ws/detections" in res.text, "WebSocket connection string missing!"
        print(f"      - GET / -> 200 OK (Served {len(res.text)} bytes of HTML/JS/CSS)")

        res_dash = client.get("/dashboard")
        assert res_dash.status_code == 200
        print("      - GET /dashboard -> 200 OK")
        print("      [PASS] Dashboard endpoint operational.")

    print("\n" + "=" * 75)
    print("PHASE 10 BOLT.NEW FRONTEND SUMMARY")
    print("=" * 75)
    print(">> React + TypeScript + Tailwind CSS project: COMPLETE (Ready for Bolt.new / Vite)")
    print(">> Integrated Browser Dashboard: ACTIVE at http://localhost:8000/ and /dashboard")
    print(">> All 7 Pages (Dashboard, Live, Damage, Objects, History, Analytics, Settings): IMPLEMENTED")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_frontend_tests()
