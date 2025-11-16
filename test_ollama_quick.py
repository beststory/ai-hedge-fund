#!/usr/bin/env python3
"""Ollama 빠른 테스트"""
import requests
import json

url = "http://localhost:11434/api/chat"
payload = {
    "model": "mistral-small3.1",
    "messages": [{"role": "user", "content": "Say 'test'"}],
    "stream": False,
    "format": "json"
}

print("Ollama 테스트 시작...")
print(f"요청: {payload}")

try:
    response = requests.post(url, json=payload, timeout=60)
    print(f"상태 코드: {response.status_code}")
    print(f"응답 길이: {len(response.text)} bytes")
    print(f"응답 내용 (처음 500자):")
    print(response.text[:500])
except Exception as e:
    print(f"오류: {e}")
