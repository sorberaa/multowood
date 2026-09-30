# -*- coding: utf-8 -*-
import sys
import time
sys.path.insert(0, 'd:/osint-bot')
from fastapi.testclient import TestClient
from src.webapp import app

client = TestClient(app)

tests = [
    ('catalog', 'GET', '/api/catalog', None),
    ('username', 'POST', '/api/scan/username', {'target': 'durov'}),
    ('telegram', 'POST', '/api/scan/telegram', {'target': 'durov'}),
    ('attribution', 'POST', '/api/scan/attribution', {'target': '@durov'}),
    ('domain', 'POST', '/api/scan/domain', {'target': 'telegram.org'}),
    ('email', 'POST', '/api/scan/email', {'target': 'test@gmail.com'}),
    ('phone', 'POST', '/api/scan/phone', {'target': '+79991234567'}),
    ('ip', 'POST', '/api/scan/ip', {'target': '1.1.1.1'}),
    ('github', 'POST', '/api/scan/github', {'target': 'torvalds'}),
    ('wayback', 'POST', '/api/scan/wayback', {'target': 'example.com'}),
    ('crypto', 'POST', '/api/scan/crypto', {'target': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa'}),
    ('dorks', 'POST', '/api/tools/dorks', {'target': 'company.com'}),
    ('autorecon', 'POST', '/api/scan/autorecon', {'target': 'durov'}),
    ('ai_profiler', 'POST', '/api/scan/ai_profiler', {'target': 'durov'}),
    ('activity_tracker', 'POST', '/api/scan/activity_tracker', {'target': 'durov'}),
    ('crypto_aml', 'POST', '/api/scan/crypto_aml', {'target': '0x742d35Cc6634C0532925a3b844Bc454e4438f44e'}),
    ('face_search', 'POST', '/api/scan/face_search', {'target': 'face_sample'}),
    ('breach_audit', 'POST', '/api/scan/breach_audit', {'target': 'durov@telegram.org'}),
    ('decode', 'POST', '/api/tools/decode', {'target': 'aGVsbG8gd29ybGQ='}),
    ('myip', 'POST', '/api/scan/myip', {'target': '1.1.1.1'}),
    ('legendary_osint', 'POST', '/api/scan/legendary_osint', {'target': 'durov'}),
    ('universal', 'POST', '/api/scan/universal', {'target': 'durov', 'tool_id': 'sherlock'}),
]

print("=== STARTING COMPREHENSIVE AUDIT OF ALL OSINT MODULES ===", flush=True)

success_count = 0
failed_count = 0

for name, method, url, payload in tests:
    t0 = time.time()
    try:
        if method == 'GET':
            r = client.get(url)
        else:
            r = client.post(url, json=payload)
        elapsed = round(time.time() - t0, 2)
        data = r.json() if r.status_code == 200 else {}
        ok = r.status_code == 200 and data.get('ok') is not False
        if ok:
            success_count += 1
            print(f"✅ PASS: {name:<18} ({elapsed}s) -> keys: {list(data.keys())[:3]}", flush=True)
        else:
            failed_count += 1
            print(f"❌ FAIL: {name:<18} ({elapsed}s) -> code: {r.status_code}, err: {data.get('error', 'unknown')}", flush=True)
    except Exception as e:
        failed_count += 1
        elapsed = round(time.time() - t0, 2)
        print(f"❌ ERROR: {name:<17} ({elapsed}s) -> {e}", flush=True)

print(f"\nAUDIT SUMMARY: {success_count} PASSED, {failed_count} FAILED out of {len(tests)} modules.", flush=True)
