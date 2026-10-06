# -*- coding: utf-8 -*-
"""Комплексный аудит всех модулей Multiwood (запуск при живом сервере или через TestClient-замены)."""
import sys
import time
from pathlib import Path

# фикс: путь берётся от расположения скрипта, а не хардкод d:/osint-bot
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import httpx  # noqa

LOCAL_API = "http://127.0.0.1:8000"
ADMIN_HEADERS = {"X-Telegram-User-Id": "5233450569"}

tests = [
    ('health', 'GET', '/health', None, None),
    ('catalog', 'GET', '/api/catalog', None, None),
    ('profile', 'POST', '/api/user/profile',
     {"tg_id": "5233450569", "tg_username": "admin", "tg_name": "Admin"}, None),
    ('admin_stats', 'GET', '/api/admin/stats', None, ADMIN_HEADERS),
    ('admin_users', 'GET', '/api/admin/users', None, ADMIN_HEADERS),
    ('admin_visitors', 'GET', '/api/admin/visitors', None, ADMIN_HEADERS),
    ('leaderboard', 'GET', '/api/user/leaderboard', None, None),
    ('username', 'POST', '/api/scan/username', {'target': 'durov'}, None),
    ('attribution', 'POST', '/api/scan/attribution', {'target': '@durov'}, None),
    ('dorks', 'POST', '/api/tools/dorks', {'target': 'company.com'}, None),
    ('decode', 'POST', '/api/tools/decode', {'target': 'aGVsbG8gd29ybGQ='}, None),
    ('phone', 'POST', '/api/scan/phone', {'target': '+79991234567'}, None),
    ('email', 'POST', '/api/scan/email', {'target': 'test@gmail.com'}, None),
    ('domain', 'POST', '/api/scan/domain', {'target': 'telegram.org'}, None),
    ('ip', 'POST', '/api/scan/ip', {'target': '1.1.1.1'}, None),
    ('myip', 'POST', '/api/scan/myip', {}, None),
    ('telegram', 'POST', '/api/scan/telegram', {'target': 'durov'}, None),
    ('github', 'POST', '/api/scan/github', {'target': 'torvalds'}, None),
    ('password', 'POST', '/api/multitool/password',
     {'length': 16, 'use_upper': True, 'use_digits': True, 'use_symbols': True}, None),
]

print("=== STARTING COMPREHENSIVE AUDIT OF ALL MODULES ===", flush=True)

success_count = 0
failed_count = 0

with httpx.Client(base_url=LOCAL_API, timeout=60.0) as client:
    for name, method, url, payload, headers in tests:
        t0 = time.time()
        try:
            if method == 'GET':
                r = client.get(url, headers=headers)
            else:
                r = client.post(url, json=payload, headers=headers)
            elapsed = round(time.time() - t0, 2)
            try:
                data = r.json() if r.status_code == 200 else {}
            except Exception:
                data = {}
            ok = r.status_code == 200 and data.get('ok') is not False
            if ok:
                success_count += 1
                print(f"PASS: {name:<18} ({elapsed}s) -> keys: {list(data.keys())[:3]}", flush=True)
            else:
                failed_count += 1
                print(f"FAIL: {name:<18} ({elapsed}s) -> code: {r.status_code}, err: {data.get('error', 'unknown')}", flush=True)
        except Exception as e:
            failed_count += 1
            elapsed = round(time.time() - t0, 2)
            print(f"ERROR: {name:<17} ({elapsed}s) -> {e}", flush=True)

print(f"\nAUDIT SUMMARY: {success_count} PASSED, {failed_count} FAILED out of {len(tests)} modules.", flush=True)
sys.exit(0 if failed_count == 0 else 1)

