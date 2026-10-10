@echo off
title Phishing Guard Launcher
net start MongoDB >nul 2>&1
start "Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\python.exe -m uvicorn server:app --reload --port 8001"
start "Frontend" cmd /k "cd /d %~dp0frontend && npm start"