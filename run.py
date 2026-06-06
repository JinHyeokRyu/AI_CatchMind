#!/usr/bin/env python
import subprocess
import time
import requests
import sys
import os

print("🚀 서버 시작 중...")
server_proc = subprocess.Popen(
    ["uvicorn", "server:app"],
)

print("⏳ 서버 준비 중...")
max_retries = 30
for i in range(max_retries):
    try:
        response = requests.get("http://localhost:8000", timeout=1)
        print("✅ 서버 준비 완료!")
        time.sleep(1)
        break
    except:
        time.sleep(1)
else:
    print("❌ 서버 시작 실패")
    server_proc.terminate()
    sys.exit(1)

print("🎮 게임 클라이언트 시작...")
client_proc = subprocess.Popen([sys.executable, "game_client.py"])

try:
    client_proc.wait()
finally:
    print("🛑 서버 종료 중...")
    server_proc.terminate()
    server_proc.wait(timeout=5)
    print("✅ 완료")
