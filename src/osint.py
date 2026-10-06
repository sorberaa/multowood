"""
Multiwood OSINT Engine — образовательные модули разведки открытых данных.

Все модули работают ТОЛЬКО с публичными данными и предназначены для обучения.
Живое использование против людей без согласия запрещено.

Модули:
  * UsernameScanner — поиск никнейма по базе sherlock_data.json (реальные HTTP-проверки)
  * PhoneRecon      — анализ номера через библиотеку phonenumbers (офлайн)
  * DomainRecon     — DNS-разведка домена + HTTP-проба
  * далее: IP, Email, Dorks, Telegram, Github, Wayback, Attribution, Universal
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("osint")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SHERLOCK_FILE = DATA_DIR / "sherlock_data.json"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

_sherlock_cache: Optional[Dict[str, Any]] = None


def _load_sherlock() -> Dict[str, Any]:
    global _sherlock_cache
    if _sherlock_cache is None:
        try:
            raw = json.loads(SHERLOCK_FILE.read_text(encoding="utf-8"))
            _sherlock_cache = {
                k: v for k, v in raw.items()
                if isinstance(v, dict) and ("url" in v or "urlProbe" in v)
            }
        except Exception as e:
            logger.error(f"sherlock data load failed: {e}")
            _sherlock_cache = {}
    return _sherlock_cache


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# =====================================================================
# 1. USERNAME SCANNER (sherlock-style, реальные проверки)
# =====================================================================

class UsernameScanner:
    MAX_SITES = 60          # лимит сайтов за один запрос (скорость)
    CONCURRENCY = 20
    TIMEOUT = 7.0

    @classmethod
    async def scan(cls, username: str, max_sites: Optional[int] = None) -> Dict[str, Any]:
        username = (username or "").strip().lstrip("@")
        if not username or len(username) > 64 or not re.fullmatch(r"[A-Za-z0-9_.\-]+", username):
            return {"ok": False, "error": "Некорректный никнейм (допустимы: буквы, цифры, _ . -)"}

        sites = _load_sherlock()
        if not sites:
            return {"ok": False, "error": "База sherlock_data.json не найдена"}

        priority = [
            "telegram", "instagram", "twitter", "tiktok", "reddit", "youtube",
            "github", "pinterest", "facebook", "linkedin", "twitch", "vimeo",
            "soundcloud", "steam", "spotify", "snapchat", "medium", "quora",
        ]
        ordered = sorted(
            sites.items(),
            key=lambda kv: min(
                (i for i, p in enumerate(priority)
                 if p in kv[0].lower() or p in str(kv[1]).lower()),
                default=999,
            ),
        )
        limit = max_sites or cls.MAX_SITES
        targets = ordered[:limit]

        found: List[Dict[str, str]] = []
        checked = 0
        sem = asyncio.Semaphore(cls.CONCURRENCY)

        async with httpx.AsyncClient(
            timeout=cls.TIMEOUT, follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        ) as client:

            async def check(site: str, meta: Dict[str, Any]) -> None:
                nonlocal checked
                url_tpl = meta.get("urlProbe") or meta.get("url")
                if not url_tpl:
                    return
                regex_check = meta.get("regexCheck")
                if regex_check:
                    try:
                        if not re.fullmatch(regex_check, username):
                            return
                    except re.error:
                        pass
                url = url_tpl.replace("{}", username)
                async with sem:
                    try:
                        r = await client.get(url)
                        checked += 1
                        if cls._exists(r, meta):
                            found.append({
                                "site": site,
                                "url": str(r.url) if r.status_code == 200 else url,
                                "status": r.status_code,
                            })
                    except Exception:
                        checked += 1

            await asyncio.gather(*(check(s, m) for s, m in targets))

        found.sort(key=lambda x: x["site"].lower())
        return {
            "ok": True,
            "target": username,
            "found_count": len(found),
            "checked_sites": checked,
            "profiles": found,
            "scanned_at": _now(),
        }

    @staticmethod
    def _exists(r: httpx.Response, meta: Dict[str, Any]) -> bool:
        if r.status_code in (404, 410):
            return False
        error_type = meta.get("errorType", "status_code")
        if error_type == "status_code":
            return r.status_code == 200
        if error_type == "message":
            text = r.text or ""
            for msg in meta.get("errorMsg", []) or []:
                if msg and msg in text:
                    return False
            return r.status_code == 200
        if error_type == "response_url":
            final = str(r.url)
            return r.status_code == 200 and "/404" not in final and "not-found" not in final.lower()
        return r.status_code == 200


# =====================================================================
# 2. PHONE RECON (phonenumbers, офлайн)
# =====================================================================

class PhoneRecon:
    @staticmethod
    def analyze(raw: str) -> Dict[str, Any]:
        try:
            import phonenumbers as pn
        except ImportError:
            return {"ok": False, "error": "Библиотека phonenumbers не установлена"}
        raw = (raw or "").strip().replace(" ", "").replace("-", "")
        if not raw:
            return {"ok": False, "error": "Номер не указан"}
        try:
            if raw[0].isdigit() and not raw.startswith("+"):
                raw = "+" + raw
            num = pn.parse(raw, None)
        except Exception:
            return {"ok": False, "error": "Не удалось разобрать номер"}
        if not pn.is_valid_number(num):
            return {"ok": False, "error": "Номер невалиден"}

        region = pn.region_code_for_number(num) or "N/A"
        try:
            geo_obj = pn.description_for_number(num, "ru") or pn.description_for_number(num, "en")
            geo = (geo_obj.description if geo_obj and geo_obj.description else "") or ""
        except Exception:
            geo = ""
        carrier = None
        try:
            from phonenumbers import carrier as pn_carrier
            carrier = (pn_carrier.name_for_number(num, "ru")
                       or pn_carrier.name_for_number(num, "en"))
        except Exception:
            carrier = None
        carrier = carrier or "N/A"
        line_type_map = {
            pn.PhoneNumberType.MOBILE: "mobile",
            pn.PhoneNumberType.FIXED_LINE: "fixed_line",
            pn.PhoneNumberType.FIXED_LINE_OR_MOBILE: "fixed_or_mobile",
            pn.PhoneNumberType.VOIP: "voip",
            pn.PhoneNumberType.TOLL_FREE: "toll_free",
            pn.PhoneNumberType.PREMIUM_RATE: "premium_rate",
        }
        line_type = line_type_map.get(pn.number_type(num), "unknown")
        return {
            "ok": True,
            "target": raw,
            "country": geo or region,
            "country_code": f"+{num.country_code}",
            "national_number": str(num.national_number or ""),
            "region": region,
            "location": geo or "N/A",
            "carrier": carrier,
            "line_type": line_type,
            "valid": True,
            "possible": pn.is_possible_number(num),
            "formatted_international": pn.format_number(num, pn.PhoneNumberFormat.INTERNATIONAL),
            "formatted_e164": pn.format_number(num, pn.PhoneNumberFormat.E164),
            "formatted_national": pn.format_number(num, pn.PhoneNumberFormat.NATIONAL),
            "warning": "Только публичные метаданные номера. Определение абонента без согласия запрещено.",
            "scanned_at": _now(),
        }


# =====================================================================
# 3. DOMAIN RECON (DNS + HTTP-проба)
# =====================================================================

class DomainRecon:
    @staticmethod
    async def analyze(domain: str) -> Dict[str, Any]:
        domain = (domain or "").strip().lower()
        domain = re.sub(r"^https?://", "", domain).split("/")[0].split("?")[0]
        if not domain or not re.fullmatch(r"[a-z0-9.\-]+\.[a-z]{2,}", domain):
            return {"ok": False, "error": "Некорректный домен"}

        loop = asyncio.get_running_loop()
        ips: List[str] = []
        dns_error = None
        try:
            infos = await loop.getaddrinfo(domain, None)
            ips = sorted({i[4][0] for i in infos})
        except Exception as e:
            dns_error = str(e)

        http_info: Dict[str, Any] = {}
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True,
                                         headers={"User-Agent": _USER_AGENT}) as client:
                r = await client.get(f"https://{domain}")
                http_info = {
                    "status_code": r.status_code,
                    "final_url": str(r.url),
                    "server": r.headers.get("server", "N/A"),
                    "https": True,
                    "hsts": "strict-transport-security" in r.headers,
                }
        except Exception as e:
            http_info = {"error": str(e)[:200]}

        return {
            "ok": True,
            "target": domain,
            "data": {
                "ip_addresses": ips,
                "dns_error": dns_error,
                "http": http_info,
            },
            "scanned_at": _now(),
        }


# =====================================================================
# 4. IP GEOINT (api.ipapi.co, публичный геолокатор)
# =====================================================================

class IpGeoint:
    # цепочка публичных геолокаторов (без ключей) — пробуем по порядку
    ENDPOINTS = [
        ("ipapi.co", "https://ipapi.co/{ip}/json/", "_ipapi_co"),
        ("ipwho.is", "https://ipwho.is/{ip}", "_ipwho_is"),
        ("ip-api.com", "http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,regionName,city,lat,lon,isp,org,as,query", "_ip_api"),
    ]

    @classmethod
    async def analyze(cls, ip: str) -> Dict[str, Any]:
        ip = (ip or "").strip()
        if not re.fullmatch(r"[0-9a-fA-F:.]+", ip) or not ip:
            return {"ok": False, "error": "Некорректный IP-адрес"}
        last_error = "все геолокаторы недоступны"
        async with httpx.AsyncClient(timeout=8.0, headers={"User-Agent": _USER_AGENT}) as client:
            for name, tpl, parser in cls.ENDPOINTS:
                try:
                    r = await client.get(tpl.format(ip=ip))
                    if r.status_code != 200:
                        last_error = f"{name}: HTTP {r.status_code}"
                        continue
                    d = r.json()
                    parsed = getattr(cls, parser)(d)
                    if parsed is None:
                        last_error = f"{name}: пустой ответ"
                        continue
                    return {
                        "ok": True,
                        "target": ip,
                        "source": name,
                        "data": parsed,
                        "scanned_at": _now(),
                    }
                except Exception as e:
                    last_error = f"{name}: {str(e)[:100]}"
        return {"ok": False, "error": f"Геолокация недоступна ({last_error})"}

    @staticmethod
    def _ipapi_co(d: dict) -> Optional[dict]:
        if d.get("error") or not d.get("country_name"):
            return None
        return {
            "ip": d.get("ip"),
            "country": d.get("country_name"),
            "country_code": d.get("country_code"),
            "region": d.get("region"),
            "city": d.get("city"),
            "latitude": d.get("latitude"),
            "longitude": d.get("longitude"),
            "asn": d.get("asn"),
            "org": d.get("org"),
            "timezone": d.get("timezone"),
            "is_proxy": bool(d.get("proxy")),
        }

    @staticmethod
    def _ipwho_is(d: dict) -> Optional[dict]:
        if not d.get("success") and d.get("success") is not None:
            return None
        if not d.get("country"):
            return None
        return {
            "ip": d.get("ip"),
            "country": d.get("country"),
            "country_code": d.get("country_code"),
            "region": d.get("region"),
            "city": d.get("city"),
            "latitude": d.get("latitude"),
            "longitude": d.get("longitude"),
            "asn": (d.get("connection") or {}).get("asn"),
            "org": (d.get("connection") or {}).get("org"),
            "timezone": (d.get("timezone") or {}).get("id"),
            "is_proxy": bool(d.get("proxy")),
        }

    @staticmethod
    def _ip_api(d: dict) -> Optional[dict]:
        if d.get("status") != "success":
            return None
        return {
            "ip": d.get("query"),
            "country": d.get("country"),
            "country_code": d.get("countryCode"),
            "region": d.get("regionName"),
            "city": d.get("city"),
            "latitude": d.get("lat"),
            "longitude": d.get("lon"),
            "asn": (d.get("as") or "").split(" ")[0] if d.get("as") else None,
            "org": d.get("isp"),
            "timezone": None,
            "is_proxy": False,
        }



# =====================================================================
# 5. EMAIL RECON (формат + MX через публичный DNS)
# =====================================================================

class EmailRecon:
    @staticmethod
    async def analyze(email: str) -> Dict[str, Any]:
        email = (email or "").strip().lower()
        if not re.fullmatch(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}", email):
            return {"ok": False, "error": "Некорректный email"}
        domain = email.split("@", 1)[1]
        loop = asyncio.get_running_loop()
        mx: List[str] = []
        mx_error = None
        try:
            # публичный DNS-over-HTTPS (Cloudflare) — без привязки к локальному резолверу
            async with httpx.AsyncClient(timeout=6.0) as client:
                r = await client.get(
                    "https://cloudflare-dns.com/dns-query",
                    params={"name": domain, "type": "MX"},
                    headers={"Accept": "application/dns-json"},
                )
                if r.status_code == 200:
                    for ans in r.json().get("Answer", []):
                        if ans.get("type") == 15:  # MX
                            mx.append(str(ans.get("data", "")).strip().rstrip("."))
        except Exception as e:
            mx_error = str(e)[:150]

        free_providers = {
            "gmail.com", "outlook.com", "hotmail.com", "yahoo.com",
            "mail.ru", "yandex.ru", "proton.me", "protonmail.com", "icloud.com",
        }
        return {
            "ok": True,
            "target": email,
            "data": {
                "domain": domain,
                "mx_records": mx,
                "mx_error": mx_error,
                "is_free_provider": domain in free_providers,
                "disposable": domain in {
                    "mailinator.com", "tempmail.com", "1secmail.com",
                    "guerrillamail.com", "yopmail.com", "trashmail.com",
                },
            },
            "scanned_at": _now(),
        }


# =====================================================================
# 6. GOOGLE DORKS (генератор учебных запросов, офлайн)
# =====================================================================

class GoogleDorks:
    TEMPLATES = [
        ("Файлы в открытом доступе", 'site:{t} filetype:pdf'),
        ("Страницы входа", 'site:{t} inurl:login'),
        ("Служебные страницы", 'site:{t} intitle:"index of"'),
        ("Упоминания на форумах", '{t} site:reddit.com OR site:quora.com'),
        ("Документы (doc/docx)", '{t} filetype:doc OR filetype:docx'),
        ("Скриншоты конфигов", '{t} filetype:env OR filetype:yml "password"'),
        ("Профили соцсетей", '"{t}" site:github.com OR site:linkedin.com OR site:t.me'),
        ("Ошибки и утечки", 'error "{t}" site:pastebin.com OR site:github.com'),
    ]

    @classmethod
    def generate(cls, target: str) -> Dict[str, Any]:
        target = (target or "").strip()
        if not target or len(target) > 120:
            return {"ok": False, "error": "Укажите компанию, домен или имя (до 120 символов)"}
        dorks = [
            {"title": title, "query": tpl.replace("{t}", target),
             "url": "https://www.google.com/search?q="
                    + urllib.parse.quote_plus(tpl.replace("{t}", target))}
            for title, tpl in cls.TEMPLATES
        ]
        return {
            "ok": True,
            "target": target,
            "count": len(dorks),
            "dorks": dorks,
            "warning": "Используйте только для защиты собственной инфраструктуры и учебных целей.",
            "scanned_at": _now(),
        }


# =====================================================================
# 7. TELEGRAM RECON (публичная страница t.me)
# =====================================================================

class TelegramRecon:
    @staticmethod
    async def analyze(username: str) -> Dict[str, Any]:
        username = (username or "").strip().lstrip("@")
        if not re.fullmatch(r"[A-Za-z0-9_]{4,32}", username):
            return {"ok": False, "error": "Некорректный Telegram-username (4-32 символа)"}
        url = f"https://t.me/{username}"
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True,
                                         headers={"User-Agent": _USER_AGENT}) as client:
                r = await client.get(url)
                text = r.text
                # Telegram возвращает 200 и для несуществующих; ловим маркеры
                not_found = "If you have Telegram, you can contact" in text and "tgme_page_description" not in text
                exists = "tgme_page_title" in text and not not_found
                desc_m = re.search(r'property="og:description"\s+content="([^"]*)"', text)
                title_m = re.search(r'property="og:title"\s+content="([^"]*)"', text)
                return {
                    "ok": True,
                    "target": username,
                    "data": {
                        "url": url,
                        "exists": exists,
                        "title": title_m.group(1) if title_m else "",
                        "description": (desc_m.group(1) if desc_m else "")[:300],
                        "http_status": r.status_code,
                    },
                    "scanned_at": _now(),
                }
        except Exception as e:
            return {"ok": False, "error": f"Сбой запроса t.me: {str(e)[:150]}"}


# =====================================================================
# 8. GITHUB RECON (публичный REST API)
# =====================================================================

class GithubRecon:
    @staticmethod
    async def analyze(username: str) -> Dict[str, Any]:
        username = (username or "").strip().lstrip("@")
        if not re.fullmatch(r"[A-Za-z0-9\-]{1,39}", username):
            return {"ok": False, "error": "Некорректный GitHub-username"}
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True,
                                         headers={"User-Agent": _USER_AGENT}) as client:
                r = await client.get(f"https://api.github.com/users/{username}")
                if r.status_code == 404:
                    return {"ok": True, "target": username,
                            "data": {"exists": False}, "scanned_at": _now()}
                if r.status_code != 200:
                    return {"ok": False, "error": f"GitHub API HTTP {r.status_code}"}
                d = r.json()
                return {
                    "ok": True,
                    "target": username,
                    "data": {
                        "exists": True,
                        "name": d.get("name"),
                        "bio": (d.get("bio") or "")[:300],
                        "company": d.get("company"),
                        "location": d.get("location"),
                        "blog": d.get("blog"),
                        "public_repos": d.get("public_repos"),
                        "followers": d.get("followers"),
                        "created_at": d.get("created_at"),
                        "profile": d.get("html_url"),
                    },
                    "scanned_at": _now(),
                }
        except Exception as e:
            return {"ok": False, "error": f"Сбой GitHub API: {str(e)[:150]}"}

            {"title": title, "query": tpl.replace("{t}", target),
             "url": "https://www.google.com/search?q=" + httpx.QueryParams({"q": tpl.replace("{t}", target)})["q"]}


# =====================================================================
# 9. WAYBACK RECON (архив.org — история снимков)
# =====================================================================

class WaybackRecon:
    @staticmethod
    async def analyze(target: str) -> Dict[str, Any]:
        target = (target or "").strip().lower()
        target = re.sub(r"^https?://", "", target).split("/")[0]
        if not re.fullmatch(r"[a-z0-9.\-]+\.[a-z]{2,}", target):
            return {"ok": False, "error": "Некорректный домен"}
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True,
                                         headers={"User-Agent": _USER_AGENT}) as client:
                r = await client.get(
                    "https://web.archive.org/cdx/search/cdx",
                    params={"url": target, "output": "json",
                            "limit": "20", "collapse": "timestamp:8",
                            "filter": "statuscode:200"},
                )
                snapshots: List[Dict[str, str]] = []
                if r.status_code == 200:
                    rows = r.json()
                    if isinstance(rows, list) and len(rows) > 1:
                        header = rows[0]
                        idx_ts = header.index("timestamp") if "timestamp" in header else 2
                        idx_orig = header.index("original") if "original" in header else 4
                        for row in rows[1:]:
                            if len(row) > max(idx_ts, idx_orig):
                                ts = row[idx_ts]
                                snapshots.append({
                                    "date": f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}",
                                    "url": f"https://web.archive.org/web/{ts}/{row[idx_orig]}",
                                })
                return {
                    "ok": True,
                    "target": target,
                    "data": {
                        "snapshots_found": len(snapshots),
                        "snapshots": snapshots[:10],
                        "archive_url": f"https://web.archive.org/web/*/{target}",
                    },
                    "scanned_at": _now(),
                }
        except Exception as e:
            return {"ok": False, "error": f"Сбой Wayback API: {str(e)[:150]}"}


# =====================================================================
# 10. ATTRIBUTION (детектор «корневого» хэндла, офлайн-эвристика)
# =====================================================================

class Attribution:
    _NOISE_SUFFIX = re.compile(
        r"(_?\d{2,4}|_(?:x?x|official|real|alt|alt2?|main|acc|account)\d*)$", re.I
    )

    @classmethod
    def analyze(cls, handle: str, text_sample: str = "") -> Dict[str, Any]:
        handle = (handle or "").strip().lstrip("@").lower()
        if not handle or len(handle) > 64:
            return {"ok": False, "error": "Укажите хэндл (@username)"}
        root = handle
        for _ in range(3):
            stripped = cls._NOISE_SUFFIX.sub("", root)
            if stripped == root:
                break
            root = stripped
        root = re.sub(r"[._]", "", root)

        signals: List[str] = []
        if re.search(r"\d{2,4}$", handle):
            signals.append("Год/цифры в конце — типичный паттерн «вирта»")
        if re.search(r"(_alt|alt\d|_real|_official|_\d+$)", handle):
            signals.append("Дополнительный суффикс — признак дубля аккаунта")
        if handle.count("_") >= 2:
            signals.append("Много разделителей _ — необычно для основного аккаунта")
        style_notes: List[str] = []
        if text_sample:
            emoji = len(re.findall(r"[\U0001F300-\U0001FAFF]", text_sample))
            if emoji >= 5:
                style_notes.append(f"Много эмодзи ({emoji}) — м.б. шаблонный стиль")
        return {
            "ok": True,
            "target": handle,
            "root_handle": root,
            "is_variant": root != handle,
            "signals": signals,
            "style_notes": style_notes,
            "confidence": min(95, 40 + 15 * len(signals) + 10 * len(style_notes)),
            "warning": "Эвристика, не доказательство. Относитесь к результатам критично.",
            "scanned_at": _now(),
        }


# =====================================================================
# 11. UNIVERSAL RECON — автодетект цели → автодосье
# =====================================================================

class UniversalRecon:
    @classmethod
    async def analyze(cls, target: str) -> Dict[str, Any]:
        target = (target or "").strip()
        if not target:
            return {"ok": False, "error": "Цель не указана"}
        modules: List[str] = []
        results: Dict[str, Any] = {}

        if target.startswith("@") or re.fullmatch(r"[A-Za-z0-9_]{4,32}", target):
            modules = ["username", "telegram", "github"]
        elif re.fullmatch(r"[+0-9()\-\s]{7,20}", target):
            modules = ["phone"]
        elif re.fullmatch(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}", target):
            modules = ["email"]
        elif re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", target):
            modules = ["ip"]
        elif re.fullmatch(r"[a-z0-9.\-]+\.[a-z]{2,}", target):
            modules = ["domain", "wayback"]
        else:
            modules = ["dorks"]

        for m in modules:
            try:
                if m == "username":
                    results[m] = await UsernameScanner.scan(target, max_sites=25)
                elif m == "telegram":
                    results[m] = await TelegramRecon.analyze(target.lstrip("@"))
                elif m == "github":
                    results[m] = await GithubRecon.analyze(target.lstrip("@"))
                elif m == "phone":
                    results[m] = PhoneRecon.analyze(target)
                elif m == "email":
                    results[m] = await EmailRecon.analyze(target)
                elif m == "ip":
                    results[m] = await IpGeoint.analyze(target)
                elif m == "domain":
                    results[m] = await DomainRecon.analyze(target)
                elif m == "wayback":
                    results[m] = await WaybackRecon.analyze(target)
                elif m == "dorks":
                    results[m] = GoogleDorks.generate(target)
            except Exception as e:
                results[m] = {"ok": False, "error": str(e)[:150]}

        ok_any = any(v.get("ok") for v in results.values())
        return {
            "ok": ok_any,
            "target": target,
            "modules": modules,
            "report": results,
            "generated_at": _now(),
            "warning": "Образовательное досье по публичным данным. Не использовать против людей без согласия.",
        }

