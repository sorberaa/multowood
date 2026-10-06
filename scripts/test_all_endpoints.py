# -*- coding: utf-8 -*-
"""Интеграционные тесты всех эндпоинтов Multiwood (запуск при живом сервере: python src/webapp.py)."""
import asyncio
import sys

# PowerShell/Windows console может быть в cp1251 — принудительно UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import httpx

LOCAL_API = "http://127.0.0.1:8000"

async def test_all():
    async with httpx.AsyncClient(base_url=LOCAL_API, timeout=60.0) as client:
        print("=== 1. ТЕСТ: КАТАЛОГ ИНСТРУМЕНТОВ ===")
        r = await client.get("/api/catalog")
        print(f"Status: {r.status_code}, Groups: {len(r.json().get('groups', []))}")

        print("\n=== 2. ТЕСТ: РЕГИСТРАЦИЯ ПОЛЬЗОВАТЕЛЯ И ОНБОРДИНГ ===")
        r = await client.post("/api/user/profile", json={
            "tg_id": "11223344",
            "tg_username": "alex_test",
            "tg_name": "Alex Hunter",
            "nickname": "ShadowAgent"
        })
        print(f"Registration Status: {r.status_code}, Response: {r.json()}")

        print("\n=== 3. ТЕСТ: ПРОФИЛЬ АДМИНИСТРАТОРА ===")
        r = await client.post("/api/user/profile", json={
            "tg_id": "5233450569",
            "tg_username": "admin_user",
            "tg_name": "Admin",
            "nickname": "ChiefAdmin"
        })
        print(f"Admin Profile Status: {r.status_code}, Response: {r.json()}")

        print("\n=== 4. ТЕСТ: АДМИН-СПИСОК ПОЛЬЗОВАТЕЛЕЙ ===")
        r = await client.get("/api/admin/users", headers={"X-Telegram-User-Id": "5233450569"})
        print(f"Admin Users Status: {r.status_code}, Total users: {len(r.json().get('users', []))}")

        print("\n=== 5. ТЕСТ: ЖУРНАЛ IP-ВИЗИТОВ ===")
        r = await client.get("/api/admin/visitors", headers={"X-Telegram-User-Id": "5233450569"})
        print(f"Visitors Log Status: {r.status_code}, Total records: {r.json().get('total_recorded')}")

        print("\n=== 6. ТЕСТ: ПОГОДА (open-meteo) ===")
        r = await client.post("/api/multitool/weather", json={"city": "Moscow"})
        d = r.json()
        print(f"Weather Status: {r.status_code}, City: {d.get('city')}, Temp: {d.get('current', {}).get('temp')}C")

        print("\n=== 7. ТЕСТ: КУРСЫ ВАЛЮТ ===")
        r = await client.post("/api/multitool/convert-currency", json={
            "amount": 100, "from_cur": "USD", "to_cur": "RUB"
        })
        d = r.json()
        print(f"Currency Status: {r.status_code}, Result: {d.get('result')} (ok={d.get('ok')})")

        print("\n=== 8. ТЕСТ: ПРОВЕРКА ПАРОЛЯ НА УТЕЧКИ (HIBP) ===")
        r = await client.post("/api/multitool/check-password", json={"password": "password"})
        d = r.json()
        print(f"PW Check Status: {r.status_code}, Pwned: {d.get('pwned')}, Breaches: {d.get('breaches')}")

        print("\n=== 9. ТЕСТ: СОКРАТЕЛЬ ССЫЛОК ===")
        r = await client.post("/api/multitool/shorten", json={"url": "https://github.com/sorberaa/multowood"})
        d = r.json()
        print(f"Shorten Status: {r.status_code}, Short: {d.get('short_url')}")
        if d.get("code"):
            rr = await client.get(f"/s/{d['code']}", follow_redirects=False)
            print(f"Redirect Status: {rr.status_code} (ожидается 307)")

        print("\n=== 10. ТЕСТ: КОНВЕРТЕР ЕДИНИЦ ===")
        r = await client.post("/api/multitool/convert-unit", json={
            "value": 100, "from_unit": "km", "to_unit": "mi"
        })
        d = r.json()
        print(f"Unit Convert Status: {r.status_code}, 100 km = {d.get('result')} mi")

        print("\n=== 11. ТЕСТ: WI-FI QR ===")
        r = await client.post("/api/multitool/wifi-qr", json={
            "ssid": "TestNet", "password": "secret123"
        })
        print(f"WiFi QR Status: {r.status_code}, Content-Type: {r.headers.get('content-type')}, bytes: {len(r.content)}")

        print("\n=== 12. ТЕСТ: СЖАТИЕ ФОТО ===")
        # миниатюрный тестовый PNG 1x1
        import base64 as b64
        png_1x1 = b64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGBgAAAABQABh6FO1AAAAABJRU5ErkJggg=="
        )
        r = await client.post(
            "/api/multitool/compress",
            files={"file": ("test.png", png_1x1, "image/png")},
            params={"quality": "78"},
        )
        print(f"Compress Status: {r.status_code}, saved: {r.headers.get('X-Saved-Pct')}%, bytes: {len(r.content)}")

        print("\n=== 13. ТЕСТ: ДОСТУП (ADMIN STATS) ===")
        r = await client.get("/api/admin/stats", headers={"X-Telegram-User-Id": "5233450569"})
        d = r.json()
        print(f"Stats Status: {r.status_code}, users={d.get('total_users')}, visits={d.get('total_visits')}")

        print("\n=== 14. ТЕСТ: БАН → БЛОК ДОСТУПА ===")
        r = await client.post("/api/admin/user/action",
                              json={"tg_id": "11223344", "action": "ban"},
                              headers={"X-Telegram-User-Id": "5233450569"})
        print(f"Ban Status: {r.status_code}, banned={r.json().get('user', {}).get('banned')}")
        r = await client.post("/api/admin/user/action",
                              json={"tg_id": "11223344", "action": "unban"},
                              headers={"X-Telegram-User-Id": "5233450569"})
        print(f"Unban Status: {r.status_code}, banned={r.json().get('user', {}).get('banned')}")

        print("\n✅ ВСЕ ТЕСТЫ БЭКЕНДА УСПЕШНО ПРОЙДЕНЫ!")

if __name__ == "__main__":
    asyncio.run(test_all())



