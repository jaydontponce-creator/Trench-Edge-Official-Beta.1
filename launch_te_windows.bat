@echo off
cd /d %~dp0
python -m pip install -r backend\requirements.txt
start "" http://127.0.0.1:8000
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
