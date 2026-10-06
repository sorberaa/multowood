# -*- coding: utf-8 -*-
"""Локальная диагностика эндпоинтов (вызов функций напрямую, без TestClient)."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from osint import PhoneRecon, UsernameScanner, Attribution, GoogleDorks  # noqa


async def main():
    print("== phone ==")
    r = await asyncio.to_thread(PhoneRecon.analyze, "+79991234567")
    print(r)

    print("== attribution ==")
    print(Attribution.analyze("@alex_temp_2024", "привет"))

    print("== dorks ==")
    print(GoogleDorks.generate("example.com")["count"])

    print("== username (5 sites) ==")
    r = await UsernameScanner.scan("github", max_sites=5)
    print({k: r[k] for k in ("ok", "found_count", "checked_sites") if k in r})

    print("== email ==")
    from osint import EmailRecon
    print(await EmailRecon.analyze("test@gmail.com"))

    print("== domain ==")
    from osint import DomainRecon
    r = await DomainRecon.analyze("example.com")
    print(r.get("ok"), r.get("data", {}).get("ip_addresses"))

    print("== ip ==")
    from osint import IpGeoint
    print(await IpGeoint.analyze("1.1.1.1"))


if __name__ == "__main__":
    asyncio.run(main())
