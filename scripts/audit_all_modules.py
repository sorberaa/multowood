# -*- coding: utf-8 -*-
"""Комплексный аудит всех модулей Multiwood (запуск при живом сервере или через TestClient-замены)."""
import sys
import time
from pathlib import Path

# путь берётся от расположения скрипта (без хардкода абсолютных путей)
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
    ('weather', 'POST', '/api/multitool/weather', {'city': 'Moscow'}, None),
    ('rates', 'POST', '/api/multitool/rates', {}, None),
    ('currency', 'POST', '/api/multitool/convert-currency',
     {'amount': 100, 'from_cur': 'USD', 'to_cur': 'EUR'}, None),
    ('password_check', 'POST', '/api/multitool/check-password', {'password': 'password'}, None),
    ('shorten', 'POST', '/api/multitool/shorten', {'url': 'https://example.com/very/long/path'}, None),
    ('unit_convert', 'POST', '/api/multitool/convert-unit',
     {'value': 100, 'from_unit': 'km', 'to_unit': 'mi'}, None),
    ('units_list', 'GET', '/api/multitool/units', None, None),
    ('decode', 'POST', '/api/tools/decode', {'target': 'aGVsbG8gd29ybGQ='}, None),
    ('password', 'POST', '/api/multitool/password',
     {'length': 16, 'use_upper': True, 'use_digits': True, 'use_symbols': True}, None),
    ('summarize', 'POST', '/api/multitool/summarize', {'target': 'Multiwood is a multitool project for mobile users.'}, None),
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

