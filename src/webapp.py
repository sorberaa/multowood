"""
Multiwood Backend Server - FastAPI High-Performance WebApp Engine
Provides APIs for Telegram Mini App:
- Social Video/Audio Downloader (yt-dlp)
- Safe File Delivery
- Mobile Utilities: Temp Mail, Password Gen, QR, Link Cleaner, AI Summary
- Admin Panel Telemetry & Broadcast
"""

import asyncio
import html
import json
import logging
import os
import shutil
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

import accounts
from multitool import (
    AIProductivity,
    CurrencyService,
    DevSecurityTools,
    ImageCompressor,
    LinkShortener,
    MediaDownloader,
    PasswordAudit,
    TempMailService,
    UnitConverter,
    WeatherService,
    WifiQr,
)

load_dotenv("/app/config/.env")
load_dotenv("config/.env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "5233450569")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "admin123")
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
USERS_FILE = DATA_DIR / "users.json"
VISITORS_FILE = DATA_DIR / "visitors.json"
HTML_FILE = Path(__file__).resolve().parent.parent / "index.html"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("multiwood-web")

app = FastAPI(title="Multiwood Multitool API", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

START_TIME = time.time()


# =====================================================================
# VISIT LOGGER (IP, User-Agent, страна, путь)
# =====================================================================

MAX_VISITS = 2000


def load_visits() -> list:
    if not VISITORS_FILE.exists():
        return []
    try:
        data = json.loads(VISITORS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_visits(visits: list) -> None:
    try:
        VISITORS_FILE.write_text(
            json.dumps(visits[-MAX_VISITS:], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        logger.error(f"save_visits: {e}")


def record_visit(request: Request, path: str) -> None:
    try:
        headers = request.headers
        ip = (
            headers.get("cf-connecting-ip")
            or headers.get("x-forwarded-for", "").split(",")[0].strip()
            or (request.client.host if request.client else "")
        )
        visits = load_visits()
        visits.append({
            "ip": ip,
            "ua": headers.get("user-agent", "")[:200],
            "country": headers.get("cf-ipcountry", ""),
            "path": path,
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        save_visits(visits)
    except Exception as e:
        logger.error(f"record_visit: {e}")


@app.middleware("http")
async def visit_middleware(request: Request, call_next):
    # логируем только страницы и ключевые действия, не каждый статический чанк
    if request.method == "GET" and request.url.path in ("/", "/index.html"):
        record_visit(request, request.url.path)
    return await call_next(request)



# =====================================================================
# USER STORAGE & REPUTATION (делегировано модулю accounts)
# =====================================================================

def load_users() -> Dict[str, Any]:
    return accounts.load_users()


def save_users(users: Dict[str, Any]):
    accounts.save_users(users)


def track_user_activity(user_id: str, username: str = "", action: str = "download"):
    """Обновляет профиль: счётчик действия + XP."""
    if not user_id:
        return
    try:
        if accounts.get_profile(user_id) is None:
            accounts.register_user(user_id, username=username)
        elif username:
            accounts.update_profile(user_id, username=username)
        field = {"download": "downloads", "mail": "mails", "scan": "scans"}.get(action)
        if field:
            accounts.bump_counter(user_id, field)
        xp_map = {"download": accounts.XP_DOWNLOAD, "mail": accounts.XP_MAIL, "scan": accounts.XP_SCAN}
        if xp_map.get(action):
            accounts.add_xp(user_id, xp_map[action])
    except Exception as e:
        logger.error(f"track_user_activity: {e}")


def get_request_tg_user(request: Request) -> Optional[dict]:
    """Извлекает и проверяет tg-пользователя из запроса (initData → заголовок)."""
    init_data = request.headers.get("x-telegram-init-data", "").strip()
    if init_data:
        user = verify_telegram_init_data(init_data)
        if user:
            return user
    uid = request.headers.get("x-telegram-user-id", "").strip()
    if uid:
        return {"id": uid}
    return None


def is_request_banned(request: Request) -> bool:
    user = get_request_tg_user(request)
    if user and user.get("id"):
        return accounts.is_banned(user["id"])
    return False



# =====================================================================
# SECURITY & AUTHENTICATION
# =====================================================================

def verify_telegram_init_data(init_data: str) -> Optional[dict]:
    """Cryptographically verifies Telegram WebApp initData HMAC-SHA256 signature."""
    if not init_data or not BOT_TOKEN:
        return None
    try:
        import hashlib
        import hmac
        parsed = dict(urllib.parse.parse_qsl(init_data))
        hash_val = parsed.pop("hash", None)
        if not hash_val:
            return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calc_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(calc_hash, hash_val):
            u_str = parsed.get("user")
            return json.loads(u_str) if u_str else parsed
        return None
    except Exception:
        return None


def is_admin_request(request: Request) -> bool:
    adm_token = request.headers.get("x-admin-token", "").strip()
    query_token = request.query_params.get("token", "").strip() or request.query_params.get("admin_token", "").strip()
    auth_header = request.headers.get("authorization", "").replace("Bearer ", "").strip()

    if ADMIN_TOKEN and (adm_token == ADMIN_TOKEN or query_token == ADMIN_TOKEN or auth_header == ADMIN_TOKEN):
        return True

    init_data = request.headers.get("x-telegram-init-data", "").strip()
    if init_data:
        tg_user = verify_telegram_init_data(init_data)
        if tg_user and ADMIN_CHAT_ID and str(tg_user.get("id")) == str(ADMIN_CHAT_ID):
            return True

    client_ip = request.client.host if request.client else ""
    if client_ip in ("127.0.0.1", "::1", "localhost"):
        uid = request.headers.get("x-telegram-user-id", "").strip()
        if ADMIN_CHAT_ID and uid == str(ADMIN_CHAT_ID):
            return True

    return False


# =====================================================================
# REQUEST SCHEMAS
# =====================================================================

class DownloadReq(BaseModel):
    url: str
    extract_audio: bool = False


class PasswordGenReq(BaseModel):
    length: int = 16
    use_upper: bool = True
    use_digits: bool = True
    use_symbols: bool = True


class QRReq(BaseModel):
    text: str


class SummarizeReq(BaseModel):
    target: str


class BroadcastReq(BaseModel):
    message: str


class ProfileReq(BaseModel):
    tg_id: str
    tg_username: str = ""
    tg_name: str = ""
    nickname: str = ""


class NicknameReq(BaseModel):
    tg_id: str
    nickname: str


class CurrencyReq(BaseModel):
    amount: float = 1
    from_cur: str = "USD"
    to_cur: str = "RUB"


class WeatherReq(BaseModel):
    city: str


class PasswordCheckReq(BaseModel):
    password: str


class ShortenReq(BaseModel):
    url: str


class WifiQrReq(BaseModel):
    ssid: str
    password: str = ""
    encryption: str = "WPA"


class ConvertReq(BaseModel):
    value: float
    from_unit: str
    to_unit: str


class UserActionReq(BaseModel):
    tg_id: str
    action: str          # ban | unban | set_role | set_vip | remove_vip | set_nick
    value: str = ""


class DecodeReq(BaseModel):
    target: str
    action: str = "base64_decode"



# =====================================================================
# FRONTEND ROOT & HEALTHCHECK
# =====================================================================

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    if HTML_FILE.exists():
        return HTMLResponse(
            content=HTML_FILE.read_text(encoding="utf-8"),
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return HTMLResponse("<h1>Multiwood Backend Active</h1>")


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": "Multiwood Multitool", "version": "4.0"}


@app.get("/api/auth/me")
async def api_auth_me(request: Request):
    tg_user = get_request_tg_user(request)
    profile = None
    if tg_user and tg_user.get("id"):
        profile = accounts.get_profile(tg_user["id"])
        if profile is None:
            profile = accounts.register_user(
                tg_user["id"],
                username=str(tg_user.get("username", "") or ""),
                first_name=str(tg_user.get("first_name", "") or ""),
            )
    return {
        "ok": True,
        "is_admin": is_admin_request(request),
        "user": profile,
    }


# =====================================================================
# ACCOUNT SYSTEM (регистрация / профиль / ник)
# =====================================================================

@app.post("/api/user/profile")
async def api_user_profile(req: ProfileReq, request: Request):
    """Регистрация/обновление аккаунта. Роль admin — только по ADMIN_CHAT_ID."""
    tg_id = (req.tg_id or "").strip()
    if not tg_id:
        return JSONResponse({"ok": False, "error": "tg_id обязателен"}, status_code=400)
    profile = accounts.register_user(
        tg_id,
        username=req.tg_username,
        first_name=req.tg_name,
        nickname=req.nickname,
    )
    return {
        "ok": True,
        "user": profile,
        "is_admin": accounts.is_admin_id(tg_id),
        "banned": bool(profile.get("banned")) if profile else False,
    }


@app.post("/api/user/nickname")
async def api_user_nickname(req: NicknameReq):
    nick = (req.nickname or "").strip()
    if not nick or len(nick) > 24:
        return JSONResponse({"ok": False, "error": "Ник: 1-24 символа"}, status_code=400)
    profile = accounts.update_profile(req.tg_id, nickname=nick)
    if profile is None:
        profile = accounts.register_user(req.tg_id, nickname=nick)
    return {"ok": True, "user": profile}


@app.get("/api/user/leaderboard")
async def api_user_leaderboard(limit: int = 10):
    top = accounts.leaderboard(max(1, min(50, limit)))
    return {
        "ok": True,
        "top": [
            {
                "rank": i + 1,
                "nickname": u.get("nickname") or u.get("username") or u.get("first_name") or "Agent",
                "level": u.get("level", 1),
                "xp": u.get("xp", 0),
                "downloads": u.get("downloads", 0),
                "role": u.get("role", "user"),
            }
            for i, u in enumerate(top)
        ],
    }


@app.post("/api/user/daily")
async def api_user_daily(req: ProfileReq):
    return accounts.claim_daily(req.tg_id)



# =====================================================================
# MULTITOOL APIS
# =====================================================================

@app.post("/api/multitool/download")
async def api_download(req: DownloadReq, request: Request):
    tg_user = get_request_tg_user(request)
    uid = str(tg_user.get("id", "")) if tg_user else ""
    if uid and accounts.is_banned(uid):
        return JSONResponse({"ok": False, "error": "Аккаунт заблокирован администратором"}, status_code=403)
    res = await MediaDownloader.download_media(req.url, req.extract_audio)
    if res.get("ok") and uid:
        track_user_activity(uid, str(tg_user.get("username", "") or ""), action="download")
    return res



@app.get("/api/multitool/file")
async def api_serve_file(p: str):
    """
    Safely delivers downloaded media with strict Path Traversal Guard.
    """
    if not p:
        return JSONResponse({"ok": False, "error": "Файл не указан"}, status_code=400)

    base_dir = (DATA_DIR / "downloads").resolve()
    try:
        target_path = Path(p).resolve()
        target_path.relative_to(base_dir)
    except (ValueError, Exception):
        return JSONResponse({"ok": False, "error": "Доступ запрещен (Path Traversal Guard)"}, status_code=403)

    if not target_path.exists() or not target_path.is_file():
        return JSONResponse({"ok": False, "error": "Файл устарел или был удален"}, status_code=404)

    ext = target_path.suffix.lower()
    media_types = {
        ".mp4": "video/mp4",
        ".m4a": "audio/mp4",
        ".mp3": "audio/mpeg",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
    }
    mtype = media_types.get(ext, "application/octet-stream")

    return FileResponse(
        path=str(target_path),
        filename=target_path.name,
        media_type=mtype,
        headers={"Content-Disposition": f'attachment; filename="{target_path.name}"'}
    )


# --- TEMP MAIL ---
@app.get("/api/multitool/tempmail/new")
async def api_tempmail_new(request: Request):
    tg_user = get_request_tg_user(request)
    uid = str(tg_user.get("id", "")) if tg_user else ""
    if uid and accounts.is_banned(uid):
        return JSONResponse({"ok": False, "error": "Аккаунт заблокирован"}, status_code=403)
    res = await TempMailService.create_inbox()
    if res.get("ok") and uid:
        track_user_activity(uid, action="mail")
    return res



@app.get("/api/multitool/tempmail/messages")
async def api_tempmail_messages(token: str):
    return await TempMailService.get_messages(token)


@app.get("/api/multitool/tempmail/read")
async def api_tempmail_read(token: str, message_id: str):
    return await TempMailService.get_message_detail(token, message_id)


# --- UTILITIES ---
@app.post("/api/multitool/password")
async def api_password(req: PasswordGenReq):
    return DevSecurityTools.generate_password(req.length, req.use_upper, req.use_digits, req.use_symbols)


@app.post("/api/multitool/qr")
async def api_qr(req: QRReq):
    qr_bytes = DevSecurityTools.generate_qr(req.text)
    return Response(content=qr_bytes, media_type="image/png")


@app.post("/api/multitool/summarize")
async def api_summarize(req: SummarizeReq):
    return await AIProductivity.summarize_page_or_text(req.target)


# =====================================================================
# CATALOG
# =====================================================================

@app.get("/api/catalog")
async def api_catalog():
    try:
        from catalog import CATALOG
        return {"ok": True, "groups": CATALOG, "count": len(CATALOG)}
    except Exception as e:
        return {"ok": False, "error": f"Каталог недоступен: {str(e)[:150]}"}


# =====================================================================
# MULTITOOL EXTRAS (погода, курсы, пароли, ссылки, единицы, QR, фото)
# =====================================================================

async def _tool_guard(request: Request) -> Optional[JSONResponse]:
    """Бан-гард для инструментов. None — можно продолжать."""
    tg_user = get_request_tg_user(request)
    uid = str(tg_user.get("id", "")) if tg_user else ""
    if uid and accounts.is_banned(uid):
        return JSONResponse({"ok": False, "error": "Аккаунт заблокирован"}, status_code=403)
    return None


@app.post("/api/multitool/weather")
async def api_weather(req: WeatherReq, request: Request):
    guard = await _tool_guard(request)
    if guard:
        return guard
    return await WeatherService.get(req.city)


@app.get("/api/multitool/weather")
async def api_weather_get(city: str, request: Request):
    guard = await _tool_guard(request)
    if guard:
        return guard
    return await WeatherService.get(city)


@app.post("/api/multitool/rates")
async def api_rates(request: Request):
    guard = await _tool_guard(request)
    if guard:
        return guard
    return await CurrencyService.popular()


@app.post("/api/multitool/convert-currency")
async def api_convert_currency(req: CurrencyReq, request: Request):
    guard = await _tool_guard(request)
    if guard:
        return guard
    return await CurrencyService.convert(req.amount, req.from_cur, req.to_cur)


@app.post("/api/multitool/check-password")
async def api_check_password(req: PasswordCheckReq, request: Request):
    guard = await _tool_guard(request)
    if guard:
        return guard
    return await PasswordAudit.check(req.password)


@app.post("/api/multitool/shorten")
async def api_shorten(req: ShortenReq, request: Request):
    guard = await _tool_guard(request)
    if guard:
        return guard
    base = str(request.base_url).rstrip("/")
    return await LinkShortener.shorten(req.url, base_url=base)


@app.get("/s/{code}")
async def api_short_redirect(code: str):
    """Редирект короткой ссылки: /s/Ab12Cd"""
    from fastapi.responses import RedirectResponse
    target = LinkShortener.resolve(code)
    if not target:
        return JSONResponse({"ok": False, "error": "Ссылка не найдена"}, status_code=404)
    return RedirectResponse(url=target, status_code=307)


@app.get("/api/multitool/links-stats")
async def api_links_stats(request: Request):
    guard = await _tool_guard(request)
    if guard:
        return guard
    return LinkShortener.stats()


@app.post("/api/multitool/wifi-qr")
async def api_wifi_qr(req: WifiQrReq, request: Request):
    guard = await _tool_guard(request)
    if guard:
        return guard
    res = await asyncio.to_thread(WifiQr.generate, req.ssid, req.password, req.encryption)
    if not res.get("ok"):
        return JSONResponse(res, status_code=400)
    # возвращаем PNG-картинкой
    return Response(content=res["png"], media_type="image/png",
                    headers={"X-Ssid": res.get("ssid", "")})


@app.post("/api/multitool/convert-unit")
async def api_convert_unit(req: ConvertReq, request: Request):
    guard = await _tool_guard(request)
    if guard:
        return guard
    return UnitConverter.convert(req.value, req.from_unit, req.to_unit)


@app.get("/api/multitool/units")
async def api_units():
    return {"ok": True, "categories": UnitConverter.categories()}


@app.post("/api/multitool/compress")
async def api_compress_image(request: Request, quality: int = 78):
    """Сжатие фото: multipart/form-data с полем file."""
    guard = await _tool_guard(request)
    if guard:
        return guard
    try:
        form = await request.form()
        upload = form.get("file")
        if upload is None:
            return JSONResponse({"ok": False, "error": "Файл не передан (поле file)"}, status_code=400)
        data = await upload.read()
        res = await asyncio.to_thread(ImageCompressor.compress, data, quality)
        if not res.get("ok"):
            return JSONResponse(res, status_code=400)
        # отдаем сжатый JPEG + метрики в заголовках
        return Response(
            content=res["png"],
            media_type="image/jpeg",
            headers={
                "X-Original-Size": str(res["original_size"]),
                "X-New-Size": str(res["new_size"]),
                "X-Saved-Pct": str(res["saved_pct"]),
                "X-Dimensions": res.get("dimensions", ""),
            },
        )
    except Exception as e:
        return JSONResponse({"ok": False, "error": f"Сбой обработки: {str(e)[:150]}"}, status_code=500)


@app.post("/api/tools/decode")
async def api_tools_decode(req: DecodeReq):
    return DevSecurityTools.cyber_decode(req.action, req.target)




# =====================================================================
# ADMIN PANEL APIS
# =====================================================================

@app.get("/api/admin/stats")
async def api_admin_stats(request: Request):
    if not is_admin_request(request):
        return JSONResponse({"ok": False, "error": "Доступ запрещен"}, status_code=403)

    stat = accounts.admin_stats()
    disk = shutil.disk_usage(".")
    visits = load_visits()
    today = datetime.now(timezone.utc).date().isoformat()
    return {
        "ok": True,
        "total_users": stat["total_users"],
        "banned": stat["banned"],
        "vip": stat["vip"],
        "active_today": stat["active_today"],
        "total_downloads": stat["total_downloads"],
        "total_scans": stat["total_scans"],
        "total_visits": len(visits),
        "visits_today": sum(1 for v in visits if str(v.get("ts", "")).startswith(today)),
        "disk_free_gb": round(disk.free / (1024**3), 2),
        "uptime_sec": int(time.time() - START_TIME),
    }


@app.get("/api/admin/users")
async def api_admin_users(request: Request, limit: int = 200, offset: int = 0):
    if not is_admin_request(request):
        return JSONResponse({"ok": False, "error": "Доступ запрещен"}, status_code=403)
    users = accounts.list_users(limit=max(1, min(500, limit)), offset=max(0, offset))
    return {
        "ok": True,
        "total": accounts.admin_stats()["total_users"],
        "users": users,
    }



@app.post("/api/admin/user/action")
async def api_admin_user_action(req: UserActionReq, request: Request):
    """ban | unban | set_role | set_vip | remove_vip | set_nick | reset_xp"""
    if not is_admin_request(request):
        return JSONResponse({"ok": False, "error": "Доступ запрещен"}, status_code=403)

    tg_id = req.tg_id.strip()
    action = req.action.strip().lower()
    if not tg_id:
        return JSONResponse({"ok": False, "error": "tg_id не указан"}, status_code=400)

    if accounts.get_profile(tg_id) is None:
        accounts.register_user(tg_id)

    if action == "ban":
        updated = accounts.set_banned(tg_id, True)
        if updated is None:
            return JSONResponse({"ok": False, "error": "Нельзя забанить администратора"}, status_code=400)
    elif action == "unban":
        accounts.set_banned(tg_id, False)
    elif action == "set_vip":
        if not accounts.is_admin_id(tg_id):
            accounts.update_profile(tg_id, role="vip")
    elif action == "remove_vip":
        if not accounts.is_admin_id(tg_id):
            accounts.update_profile(tg_id, role="user")
    elif action == "set_role" and req.value in ("user", "vip"):
        if not accounts.is_admin_id(tg_id):
            accounts.update_profile(tg_id, role=req.value)
    elif action == "set_nick":
        accounts.update_profile(tg_id, nickname=req.value[:24])
    elif action == "reset_xp":
        accounts.update_profile(tg_id, xp=0)
    else:
        return JSONResponse({"ok": False, "error": f"Неизвестное действие: {action}"}, status_code=400)

    return {"ok": True, "user": accounts.get_profile(tg_id)}


@app.get("/api/admin/visitors")
async def api_admin_visitors(request: Request, limit: int = 100):
    if not is_admin_request(request):
        return JSONResponse({"ok": False, "error": "Доступ запрещен"}, status_code=403)
    visits = load_visits()
    return {
        "ok": True,
        "total_recorded": len(visits),
        "visits": visits[-max(1, min(500, limit)):][::-1],
    }


@app.get("/admin/visits")
async def admin_visits_legacy(request: Request, token: str = "", limit: int = 100):
    """Legacy JSON-роут из README: /admin/visits?token=ADMIN_TOKEN"""
    if token != ADMIN_TOKEN and not is_admin_request(request):
        return JSONResponse({"ok": False, "error": "Доступ запрещен"}, status_code=403)
    visits = load_visits()
    return {
        "ok": True,
        "total_recorded": len(visits),
        "visits": visits[-max(1, min(500, limit)):][::-1],
    }


@app.get("/admin/visits-html", response_class=HTMLResponse)
async def admin_visits_html(request: Request, token: str = "", limit: int = 100):
    """Красивая HTML-таблица визитов: /admin/visits-html?token=ADMIN_TOKEN"""
    if token != ADMIN_TOKEN and not is_admin_request(request):
        return HTMLResponse("<h1>403 Доступ запрещен</h1>", status_code=403)
    visits = load_visits()[-max(1, min(300, limit)):][::-1]
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(v.get('ts', '')))}</td>"
        f"<td>{html.escape(str(v.get('ip', '')))}</td>"
        f"<td>{html.escape(str(v.get('country', '')))}</td>"
        f"<td>{html.escape(str(v.get('path', '')))}</td>"
        f"<td style='max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'>"
        f"{html.escape(str(v.get('ua', '')))}</td>"
        "</tr>"
        for v in visits
    )
    page = f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<title>Multiwood — Визиты</title><style>
body{{background:#0b0f14;color:#e2e8f0;font-family:monospace;padding:24px;}}
table{{border-collapse:collapse;width:100%;font-size:13px;}}
th,td{{border:1px solid #1f2937;padding:6px 8px;text-align:left;}}
th{{background:#111827;color:#38bdf8;}}</style></head><body>
<h1>Журнал визитов (последние {len(visits)})</h1>
<table><tr><th>Время (UTC)</th><th>IP</th><th>Страна</th><th>Путь</th><th>User-Agent</th></tr>
{rows or '<tr><td colspan="5">Пока нет визитов</td></tr>'}</table></body></html>"""
    return HTMLResponse(page)


@app.post("/api/admin/broadcast")
async def api_admin_broadcast(request: Request, req: BroadcastReq):
    if not is_admin_request(request):
        return JSONResponse({"ok": False, "error": "Доступ запрещен"}, status_code=403)

    text = req.message.strip()
    if not text:
        return JSONResponse({"ok": False, "error": "Текст пустой"}, status_code=400)

    if not BOT_TOKEN:
        return JSONResponse({"ok": False, "error": "BOT_TOKEN не задан"}, status_code=500)

    target_ids = accounts.broadcaster_targets()

    sent = 0
    failed = 0
    async with httpx.AsyncClient(timeout=10.0) as client:
        for tid in target_ids:
            try:
                # 1) пробуем с HTML (админ может писать <b>...</b>)
                r = await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={"chat_id": tid, "text": text, "parse_mode": "HTML"},
                )
                if r.status_code == 200:
                    sent += 1
                else:
                    # 2) невалидный HTML → повтор без parse_mode
                    r = await client.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                        json={"chat_id": tid, "text": text},
                    )
                    if r.status_code == 200:
                        sent += 1
                    else:
                        failed += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.04)

    return {"ok": True, "total": len(target_ids), "sent": sent, "failed": failed}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)