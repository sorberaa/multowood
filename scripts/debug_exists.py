# -*- coding: utf-8 -*-
"""Точечная диагностика UsernameScanner._exists."""
import asyncio
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from osint import UsernameScanner, _load_sherlock  # noqa


async def main():
    sites = _load_sherlock()
    for name in ("Telegram", "GitHub", "Reddit", "Twitch"):
        meta = sites.get(name)
        if not meta:
            print(name, "нет в базе")
            continue
        tpl = meta.get("urlProbe") or meta.get("url")
        url = tpl.replace("{}", "github")
        try:
            async with httpx.AsyncClient(timeout=7, follow_redirects=True,
                                         headers={"User-Agent": "Mozilla/5.0"}) as c:
                r = await c.get(url)
            exists = UsernameScanner._exists(r, meta)
            print(f"{name}: status={r.status_code} errType={meta.get('errorType')} "
                  f"regexCheck={meta.get('regexCheck')} _exists={exists}")
        except Exception as e:
            print(name, "ERR", e)


if __name__ == "__main__":
    asyncio.run(main())
