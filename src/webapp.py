"""
Multiwood Backend Server - FastAPI High-Performance WebApp Engine
Provides APIs for Telegram Mini App:
- Social Video/Audio Downloader (yt-dlp)
- Safe File Delivery
- Mobile Utilities: Temp Mail, Password Gen, QR, Link Cleaner, AI Summary
- Admin Panel Telemetry & Broadcast
"""

import asyncio
import json
import logging
import os
import shutil
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

from multitool import AIProductivity, DevSecurityTools, MediaDownloader, TempMailService

load_dotenv("/app/config/.env")
load_dotenv("config/.env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "5233450569")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "admin123")
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
USERS_FILE = DATA_DIR / "users.json"
HTML_FILE = Path(__file__).resolve().parent.parent / "index.html"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("multiwood-web")

app = FastAPI(title="Multiwood Multitool API", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================================
# USER STORAGE & REPUTATION
# =====================================================================

def load_users() -> Dict[str, Any]:
    if not USERS_FILE.exists():
        return {}
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_users(users: Dict[str, Any]):
    try:
        USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error(f"Error saving users: {e}")


def track_user_activity(user_id: str, username: str = ""):
    if not user_id:
        return
    users = load_users()
    u = users.get(user_id, {})
    u["user_id"] = user_id
    if username:
        u["username"] = username
    u["downloads"] = u.get("downloads", 0) + 1
    users[user_id] = u
    save_users(users)


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
    return {"status": "ok", "app": "Multiwood Multitool", "version": "3.0"}


@app.get("/api/auth/me")
async def api_auth_me(request: Request):
    return {
        "ok": True,
        "is_admin": is_admin_request(request)
    }


# =====================================================================
# MULTITOOL APIS
# =====================================================================

@app.post("/api/multitool/download")
async def api_download(req: DownloadReq, request: Request):
    res = await MediaDownloader.download_media(req.url, req.extract_audio)
    if res.get("ok"):
        uid = request.headers.get("x-telegram-user-id", "")
        track_user_activity(uid)
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
async def api_tempmail_new():
    return await TempMailService.create_inbox()


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
# ADMIN PANEL APIS
# =====================================================================

@app.get("/api/admin/stats")
async def api_admin_stats(request: Request):
    if not is_admin_request(request):
        return JSONResponse({"ok": False, "error": "Доступ запрещен"}, status_code=403)

    users = load_users()
    stat = shutil.disk_usage(".")
    disk_free_gb = round(stat.free / (1024**3), 2)

    return {
        "ok": True,
        "total_users": max(1, len(users)),
        "disk_free_gb": disk_free_gb,
    }


@app.post("/api/admin/broadcast")
async def api_admin_broadcast(request: Request, req: BroadcastReq):
    if not is_admin_request(request):
        return JSONResponse({"ok": False, "error": "Доступ запрещен"}, status_code=403)

    text = req.message.strip()
    if not text:
        return JSONResponse({"ok": False, "error": "Текст пустой"}, status_code=400)

    if not BOT_TOKEN:
        return JSONResponse({"ok": False, "error": "BOT_TOKEN не задан"}, status_code=500)

    users = load_users()
    target_ids = [u_id for u_id in users.keys() if str(u_id).isdigit()]
    if ADMIN_CHAT_ID and str(ADMIN_CHAT_ID) not in target_ids:
        target_ids.append(str(ADMIN_CHAT_ID))

    sent = 0
    async with httpx.AsyncClient(timeout=10.0) as client:
        for tid in target_ids:
            try:
                r = await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={"chat_id": tid, "text": text, "parse_mode": "HTML"}
                )
                if r.status_code == 200:
                    sent += 1
            except Exception:
                pass
            await asyncio.sleep(0.04)

    return {"ok": True, "total": len(target_ids), "sent": sent}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)