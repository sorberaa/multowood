# -*- coding: utf-8 -*-
"""Диагностика: почему username-скан не находит известные аккаунты."""
import asyncio
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


async def main():
    data = json.loads((ROOT / "data" / "sherlock_data.json").read_text(encoding="utf-8"))
    sites = [(k, v) for k, v in data.items()
             if isinstance(v, dict) and ("url" in v or "urlProbe" in v)]
    print("всего сайтов в базе:", len(sites))
    # приоритетные из UsernameScanner
    priority = ["telegram", "instagram", "twitter", "tiktok", "reddit", "youtube",
                "github", "pinterest", "facebook", "linkedin", "twitch"]
    ordered = sorted(
        sites,
        key=lambda kv: min((i for i, p in enumerate(priority)
                            if p in kv[0].lower() or p in str(kv[1]).lower()), default=999),
    )
    print("первые 12:", [k for k, _ in ordered[:12]])

    async with httpx.AsyncClient(timeout=7, follow_redirects=True,
                                 headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}) as c:
        for k, v in ordered[:12]:
            tpl = v.get("urlProbe") or v.get("url")
            u = tpl.replace("{}", "github")
            try:
                r = await c.get(u)
                print(f"{k:20} {r.status_code} errType={v.get('errorType')} url={u[:80]}")
            except Exception as e:
                print(f"{k:20} ERR {str(e)[:60]}")

    # и прямая проверка того, что делает UsernameScanner
    from osint import UsernameScanner
    r = await UsernameScanner.scan("github", max_sites=12)
    print("scanner:", r["found_count"], "/", r["checked_sites"], r.get("profiles"))


if __name__ == "__main__":
    asyncio.run(main())
