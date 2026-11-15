# Contributing to AI Road Damage Detection System

Thank you for your interest in contributing to the **AI-Based Road Damage Detection and Real-Time Object Recognition System**! This document provides instructions for contributing code, models, documentation, and bug reports.

---

## 1. Development Principles

- **Zero-Latency Video Processing**: All computer vision frame loops must execute without blocking the main event loop. Utilize `ZeroLatencyFrameBuffer` with automatic stale-frame dropping.
- **Credential Protection**: Never commit camera passwords, API keys, private keys, or RTSP authentication URLs to version control. Always use credential masking `rtsp://<user>:********@<ip>:<port>/...`.
- **Dual Inference Integrity**: When modifying YOLO pipelines, ensure inference for both the Road Damage Model and the General Object Model remain synchronized.

---

## 2. Setting Up Your Development Environment

1. Fork and clone the repository.
2. Follow [docs/installation.md](docs/installation.md) to set up Python 3.12 and dependencies.
3. Verify your environment by running:
   ```bash
   python scripts/run_all_tests.py
   ```

---

## 3. Pull Request Guidelines

1. Create a feature branch: `git checkout -b feature/your-feature-name`.
2. Follow PEP 8 guidelines for all Python code.
3. Write modular tests in `scripts/test_<feature>.py`.
4. Ensure all 12 test suites in `scripts/run_all_tests.py` pass with a 100% score before submitting.
5. Submit a descriptive Pull Request with before/after benchmarks if modifying inference or streaming throughput.

---

## 4. Reporting Issues

Please open an issue on GitHub detailing:
- Operating System & hardware specs (CPU, GPU, RAM)
- Camera model & firmware version
- Expected vs. actual behavior
- Relevant backend logs from `backend/storage/road_ai.log`
