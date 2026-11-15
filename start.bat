@echo off
title AI Road Surveillance Engine
color 0a
echo ==============================================================================
echo  AI Road Damage Detection and Real-Time Object Recognition System
echo ==============================================================================
echo.

if not exist venv (
    echo [ERROR] Virtual environment 'venv' not found.
    echo Please create it using: python -m venv venv
    pause
    exit /b 1
)

set PORT=7860
echo Starting AI Surveillance Server on http://localhost:7860 ...
.\venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --host 0.0.0.0 --port 7860
