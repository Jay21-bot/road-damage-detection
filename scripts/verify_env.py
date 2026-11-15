#!/usr/bin/env python3
"""
Environment & Project Structure Verification Script
Validates Python runtime, project scaffolding, dependencies, and GPU capabilities.
"""

import sys
import os
from pathlib import Path
import platform
import importlib.util

REQUIRED_DIRECTORIES = [
    "backend/app/api/v1",
    "backend/app/core",
    "backend/app/db",
    "backend/app/services",
    "backend/app/schemas",
    "backend/models",
    "backend/storage/snapshots",
    "scripts",
    "docs"
]

REQUIRED_FILES = [
    "backend/requirements.txt",
    "backend/app/core/config.py",
    "backend/app/core/logging.py",
    ".env.example",
    ".gitignore",
    "LICENSE",
    "docs/architecture.md"
]

CORE_PACKAGES = [
    ("fastapi", "FastAPI Web Framework"),
    ("uvicorn", "ASGI Server"),
    ("pydantic", "Data Validation"),
    ("cv2", "OpenCV Computer Vision"),
    ("torch", "PyTorch Deep Learning"),
    ("torchvision", "PyTorch Vision Utilities"),
    ("ultralytics", "Ultralytics YOLO Engine"),
    ("sqlalchemy", "SQLAlchemy ORM"),
    ("numpy", "NumPy Numerical Computing"),
    ("websockets", "WebSocket Protocol")
]


def check_python_version() -> bool:
    print("\n[1/5] Checking Python Runtime...")
    major = sys.version_info.major
    minor = sys.version_info.minor
    patch = sys.version_info.micro
    print(f"      Running Python {major}.{minor}.{patch} on {platform.system()} ({platform.machine()})")

    if major < 3 or (major == 3 and minor < 9):
        print("      [FAIL] Python 3.9 or higher is required.")
        return False
    print("      [PASS] Python version compatible.")
    return True


def check_project_structure(root_path: Path) -> bool:
    print("\n[2/5] Checking Project Directory & File Scaffolding...")
    all_ok = True

    for rel_dir in REQUIRED_DIRECTORIES:
        dir_path = root_path / rel_dir
        if dir_path.is_dir():
            print(f"      [OK] Directory: {rel_dir}")
        else:
            print(f"      [MISSING] Directory: {rel_dir}")
            all_ok = False

    for rel_file in REQUIRED_FILES:
        file_path = root_path / rel_file
        if file_path.is_file():
            print(f"      [OK] File:      {rel_file}")
        else:
            print(f"      [MISSING] File:      {rel_file}")
            all_ok = False

    return all_ok


def check_python_packages() -> dict:
    print("\n[3/5] Checking Core AI & Backend Packages...")
    status = {}
    for pkg_name, description in CORE_PACKAGES:
        spec = importlib.util.find_spec(pkg_name)
        if spec is not None:
            try:
                mod = importlib.import_module(pkg_name)
                ver = getattr(mod, "__version__", "installed")
                print(f"      [INSTALLED] {pkg_name:<14} ({ver:<12}) - {description}")
                status[pkg_name] = True
            except Exception as e:
                print(f"      [WARNING]   {pkg_name:<14} installed but import error: {e}")
                status[pkg_name] = False
        else:
            print(f"      [NOT FOUND] {pkg_name:<14} - {description}")
            status[pkg_name] = False
    return status


def check_compute_device():
    print("\n[4/5] Checking Compute Hardware (CUDA / CPU)...")
    try:
        import torch
        cuda_avail = torch.cuda.is_available()
        if cuda_avail:
            device_name = torch.cuda.get_device_name(0)
            dev_count = torch.cuda.device_count()
            print(f"      [CUDA READY] Hardware Acceleration: {dev_count} GPU(s) available")
            print(f"                   Primary GPU: {device_name}")
        else:
            print("      [CPU MODE]   CUDA is not available. System will run in CPU inference mode.")
    except ImportError:
        print("      [INFO]       PyTorch not yet installed. Device check skipped.")


def check_configuration(root_path: Path):
    print("\n[5/5] Checking Configuration & Camera URI Builder...")
    sys.path.insert(0, str(root_path / "backend"))
    try:
        from app.core.config import settings
        rtsp_masked = settings.get_rtsp_url(mask_password=True)
        print(f"      [PASS] Config parsed successfully.")
        print(f"             Sample CP PLUS Stream URI: {rtsp_masked}")
    except Exception as e:
        print(f"      [INFO] Configuration preview note: {e}")


def main():
    print("=" * 70)
    print("AI ROAD DAMAGE & OBJECT DETECTION SYSTEM - ENVIRONMENT VERIFICATION")
    print("=" * 70)

    root = Path(__file__).resolve().parent.parent
    py_ok = check_python_version()
    struct_ok = check_project_structure(root)
    pkg_status = check_python_packages()
    check_compute_device()
    check_configuration(root)

    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    if py_ok and struct_ok:
        print(">> Project scaffolding and file tree: COMPLETE")
    else:
        print(">> Structure check encountered missing items.")

    missing = [pkg for pkg, installed in pkg_status.items() if not installed]
    if missing:
        print(f">> Missing {len(missing)} Python packages:")
        print(f"   Run: pip install -r backend/requirements.txt")
    else:
        print(">> All required Python packages are installed!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
