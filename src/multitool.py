"""
Cyber Multitool Module - High Performance & Bulletproof Security
Core engines for:
1. MediaDownloader (Social video & audio downloader via yt-dlp)
2. TempMailService (Disposable email inbox & verification reader)
3. DevSecurityTools (Password generator, Cyber decoding/hashing, Web probe & QR engine)
4. AIProductivity (Webpage text extractor & intelligent summarizer)
"""

import asyncio
import base64
import hashlib
import html
import io
import ipaddress
import json
import logging
import math
import os
import re
import secrets
import socket
import string
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    import qrcode
    from PIL import Image
except ImportError:
    qrcode = None

logger = logging.getLogger("multitool")

# Общий User-Agent для внешних запросов
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# Safe storage path for downloads
BASE_DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DOWNLOAD_DIR = BASE_DATA_DIR / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


# =====================================================================
# SECURITY HELPERS: ANTI-SSRF, INPUT SANITIZATION
# =====================================================================

def is_safe_url(url: str) -> bool:
    """
    Prevents SSRF attacks. Ensures URL scheme is http/https and
    resolved host does not point to internal/private IP ranges or loopback.
    """
    try:
        parsed = urllib.parse.urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            return False
        
        hostname = parsed.hostname
        if not hostname:
            return False

        lower_host = hostname.lower()
        if lower_host in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "local"):
            return False

        # Check if direct IP address
        try:
            ip_obj = ipaddress.ip_address(lower_host)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved or ip_obj.is_link_local or ip_obj.is_multicast:
                return False
        except ValueError:
            # It's a hostname, resolve DNS
            addr_info = socket.getaddrinfo(hostname, None)
            for entry in addr_info:
                ip_str = entry[4][0]
                ip_obj = ipaddress.ip_address(ip_str)
                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved or ip_obj.is_link_local or ip_obj.is_multicast:
                    return False

        return True
    except Exception as e:
        logger.warning(f"SSRF verification failed for URL '{url}': {e}")
        return False


def cleanup_old_files(directory: Path, max_age_seconds: int = 1800):
    """Deletes files older than max_age_seconds in download directory to prevent disk exhaustion."""
    try:
        now = time.time()
        for f in directory.glob("*"):
            if f.is_file():
                try:
                    if now - f.stat().st_mtime > max_age_seconds:
                        f.unlink(missing_ok=True)
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"Error during file cleanup: {e}")


# =====================================================================
# 1. MEDIA DOWNLOADER (TIKTOK, REELS, SHORTS, TWITTER/X, PINTEREST, ETC.)
# =====================================================================

class MediaDownloader:
    SUPPORTED_DOMAINS = [
        "tiktok.com",
        "instagram.com",
        "instagr.am",
        "youtube.com",
        "youtu.be",
        "twitter.com",
        "x.com",
        "pinterest.com",
        "pin.it",
        "reddit.com",
        "v.redd.it",
        "vk.com",
        "vkvideo.ru",
        "facebook.com",
        "fb.watch",
        "soundcloud.com",
        "likee.video",
        "threads.net",
        "twitch.tv",
        "vimeo.com",
        "dailymotion.com",
    ]

    MEDIA_EXTENSIONS = (".mp4", ".mov", ".m4v", ".webm", ".mp3", ".wav", ".m4a")

    @classmethod
    def is_media_url(cls, text: str) -> bool:
        """Determines if the text contains a recognized social or direct media link."""
        if not text:
            return False
        text_clean = text.strip()
        if not (text_clean.startswith("http://") or text_clean.startswith("https://")):
            return False

        try:
            parsed = urllib.parse.urlparse(text_clean)
            host = (parsed.hostname or "").lower()
            path = (parsed.path or "").lower()

            for domain in cls.SUPPORTED_DOMAINS:
                if host == domain or host.endswith("." + domain):
                    return True

            for ext in cls.MEDIA_EXTENSIONS:
                if path.endswith(ext):
                    return True
        except Exception:
            pass

        return False

    @classmethod
    async def download_media(cls, url: str, extract_audio: bool = False) -> Dict[str, Any]:
        """
        Downloads social media video or audio safely using yt-dlp in a worker thread.
        Guarantees no shell execution, strict timeouts, and file size limits.
        """
        url = url.strip()
        if not cls.is_media_url(url):
            return {"ok": False, "error": "Ссылка не поддерживается или не является медиа-ресурсом."}

        if not is_safe_url(url):
            return {"ok": False, "error": "Недопустимый адрес (заблокировано политикой безопасности SSRF)."}

        if yt_dlp is None:
            return {"ok": False, "error": "Модуль yt-dlp не установлен в системе."}

        # Periodic cleanup of old temporary files
        cleanup_old_files(DOWNLOAD_DIR, max_age_seconds=1800)

        file_token = secrets.token_hex(8)
        outtmpl = str(DOWNLOAD_DIR / f"dl_{file_token}_%(id)s.%(ext)s")

        ydl_opts: Dict[str, Any] = {
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
            "max_filesize": 85 * 1024 * 1024,  # 85MB max
            "retries": 2,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "http_headers": {
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                "Sec-Ch-Ua": '"Not/A)Brand";v="8", "Chromium";v="126"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
            },
        }

        if extract_audio:
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        else:
            # Target MP4 for maximum iOS and Android compatibility
            ydl_opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

        def _run_ytdl():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info

        try:
            info = await asyncio.to_thread(_run_ytdl)
            if not info:
                return {"ok": False, "error": "Не удалось извлечь информацию о медиа."}

            # Locate the output file
            downloaded_file: Optional[Path] = None
            target_prefix = f"dl_{file_token}_"
            for f in DOWNLOAD_DIR.glob(f"{target_prefix}*"):
                if f.is_file():
                    downloaded_file = f
                    break

            if not downloaded_file or not downloaded_file.exists():
                return {"ok": False, "error": "Файл не найден на диске после загрузки."}

            file_size = downloaded_file.stat().st_size
            title = info.get("title") or "Медиафайл"
            uploader = info.get("uploader") or info.get("channel") or info.get("creator") or "Неизвестный автор"
            duration = int(info.get("duration") or 0)
            thumbnail = info.get("thumbnail") or ""

            return {
                "ok": True,
                "filepath": str(downloaded_file.resolve()),
                "filename": downloaded_file.name,
                "title": title,
                "uploader": uploader,
                "duration": duration,
                "filesize": file_size,
                "thumbnail": thumbnail,
                "format": "audio/mp3" if extract_audio else "video/mp4",
            }
        except yt_dlp.utils.DownloadError as de:
            clean_err = str(de)
            if "File is larger than max-filesize" in clean_err:
                clean_err = "Размер видео превышает лимит (макс. 85 МБ)."
            return {"ok": False, "error": f"Ошибка скачивания: {clean_err}"}
        except Exception as e:
            logger.exception("Media download failure")
            return {"ok": False, "error": f"Сбой при загрузке: {str(e)}"}


# =====================================================================
# 2. TEMP MAIL SERVICE (MAIL.TM PUBLIC API — живой сервис)
# =====================================================================

class TempMailService:
    API_BASE = "https://api.mail.tm"
    _UA = {"User-Agent": "Mozilla/5.0 MultiwoodTempMail/3.0"}
    # локальные сессии: address -> {password, jwt} (файл переживает рестарт)
    SESSIONS_FILE = Path(os.getenv("DATA_DIR", "data")) / "tempmail_sessions.json"

    # ---------- helpers ----------
    @classmethod
    def _load_sessions(cls) -> Dict[str, Any]:
        try:
            if cls.SESSIONS_FILE.exists():
                return json.loads(cls.SESSIONS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    @classmethod
    def _save_sessions(cls, sessions: Dict[str, Any]) -> None:
        try:
            cls.SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            cls.SESSIONS_FILE.write_text(
                json.dumps(sessions, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"tempmail sessions save: {e}")

    @classmethod
    async def _get_jwt(cls, address: str, password: str) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=10.0, headers=cls._UA) as client:
                r = await client.post(
                    f"{cls.API_BASE}/token",
                    json={"address": address, "password": password},
                )
                if r.status_code in (200, 201):
                    return r.json().get("token")
        except Exception as e:
            logger.error(f"tempmail token: {e}")
        return None

    # ---------- public API ----------
    @classmethod
    async def create_inbox(cls) -> Dict[str, Any]:
        """Создаёт временный ящик на mail.tm. Возвращает {ok, email, token}."""
        try:
            async with httpx.AsyncClient(timeout=12.0, headers=cls._UA) as client:
                # 1. доступный домен
                rd = await client.get(f"{cls.API_BASE}/domains")
                if rd.status_code != 200:
                    return {"ok": False, "error": "Сервис почты недоступен (domains)"}
                domains = [d["domain"] for d in rd.json().get("hydra:member", [])
                           if d.get("isActive", True)]
                if not domains:
                    return {"ok": False, "error": "Нет доступных доменов почты"}
                domain = domains[0]

                # 2. уникальный логин
                for _ in range(4):
                    local = f"mw{secrets.token_hex(6)}"
                    address = f"{local}@{domain}"
                    password = secrets.token_urlsafe(16)
                    ra = await client.post(
                        f"{cls.API_BASE}/accounts",
                        json={"address": address, "password": password},
                    )
                    if ra.status_code in (200, 201):
                        jwt = await cls._get_jwt(address, password)
                        if not jwt:
                            return {"ok": False, "error": "Не удалось активировать ящик"}
                        sessions = cls._load_sessions()
                        sessions[address] = {"password": password, "jwt": jwt}
                        cls._save_sessions(sessions)
                        return {"ok": True, "email": address, "token": address}
                    if ra.status_code != 422:
                        break
                return {"ok": False, "error": "Не удалось создать ящик (занято)"}
        except Exception as e:
            logger.error(f"TempMail create error: {e}")
            return {"ok": False, "error": f"Сбой сервиса почты: {str(e)[:150]}"}


    @classmethod
    async def _authed_get(cls, address: str, path: str) -> Optional[httpx.Response]:
        sessions = cls._load_sessions()
        sess = sessions.get(address)
        if not sess:
            return None
        jwt = sess.get("jwt")
        headers = dict(cls._UA)
        if jwt:
            headers["Authorization"] = f"Bearer {jwt}"
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            r = await client.get(f"{cls.API_BASE}{path}")
            if r.status_code in (401, 403):
                # JWT протух — логинимся заново
                jwt = await cls._get_jwt(address, sess.get("password", ""))
                if not jwt:
                    return None
                sess["jwt"] = jwt
                sessions[address] = sess
                cls._save_sessions(sessions)
                headers["Authorization"] = f"Bearer {jwt}"
                r = await client.get(f"{cls.API_BASE}{path}")
            return r

    @classmethod
    async def get_messages(cls, token: str) -> Dict[str, Any]:
        """token == адрес ящика. Возвращает нормализованный список писем."""
        address = (token or "").strip().lower()
        if "@" not in address:
            return {"ok": False, "error": "Неверный формат токена почты"}
        try:
            r = await cls._authed_get(address, "/messages")
            if r is None:
                return {"ok": False, "error": "Ящик не найден (сервер перезапущен — создайте новый)"}
            if r.status_code != 200:
                return {"ok": False, "error": f"Ошибка сервера почты: HTTP {r.status_code}"}
            raw = r.json().get("hydra:member", [])
            messages = [
                {
                    "id": m.get("id"),
                    "from": (m.get("from") or {}).get("address", "?"),
                    "subject": m.get("subject") or "(без темы)",
                    "intro": (m.get("intro") or "")[:200],
                    "created_at": m.get("createdAt"),
                }
                for m in raw
            ]
            return {"ok": True, "messages": messages}
        except Exception as e:
            return {"ok": False, "error": str(e)[:150]}

    @classmethod
    async def get_message_detail(cls, token: str, message_id: str) -> Dict[str, Any]:
        address = (token or "").strip().lower()
        if "@" not in address:
            return {"ok": False, "error": "Неверный формат токена почты"}
        message_id = (message_id or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9\-]{4,64}", message_id):
            return {"ok": False, "error": "Неверный ID письма"}
        try:
            r = await cls._authed_get(address, f"/messages/{message_id}")
            if r is None:
                return {"ok": False, "error": "Ящик не найден"}
            if r.status_code != 200:
                return {"ok": False, "error": f"Письмо не найдено: HTTP {r.status_code}"}
            m = r.json()
            return {
                "ok": True,
                "message": {
                    "id": m.get("id"),
                    "from": (m.get("from") or {}).get("address", "?"),
                    "subject": m.get("subject") or "(без темы)",
                    "text": m.get("text") or "",
                    "created_at": m.get("createdAt"),
                },
            }
        except Exception as e:
            return {"ok": False, "error": str(e)[:150]}



# =====================================================================
# 3. DEV & SECURITY UTILITIES
# =====================================================================

class DevSecurityTools:
    @staticmethod
    def generate_password(length: int = 16, use_upper: bool = True, use_digits: bool = True, use_symbols: bool = True) -> Dict[str, Any]:
        """Generates cryptographically secure password with entropy metrics."""
        length = max(8, min(64, length))
        chars = list(string.ascii_lowercase)
        required_chars = [secrets.choice(string.ascii_lowercase)]

        if use_upper:
            chars.extend(string.ascii_uppercase)
            required_chars.append(secrets.choice(string.ascii_uppercase))
        if use_digits:
            chars.extend(string.digits)
            required_chars.append(secrets.choice(string.digits))
        if use_symbols:
            symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            chars.extend(symbols)
            required_chars.append(secrets.choice(symbols))

        # Fill remaining length
        remaining = [secrets.choice(chars) for _ in range(length - len(required_chars))]
        all_chars = required_chars + remaining
        secrets.SystemRandom().shuffle(all_chars)
        pwd = "".join(all_chars)

        pool_size = len(set(chars))
        entropy = round(length * math.log2(pool_size), 1)

        strength = "Слабый"
        if entropy >= 80:
            strength = "Очень надежный (Военный класс)"
        elif entropy >= 60:
            strength = "Надежный"
        elif entropy >= 40:
            strength = "Средний"

        return {
            "ok": True,
            "password": pwd,
            "entropy": entropy,
            "strength": strength,
            "length": length,
        }

    @staticmethod
    def cyber_decode(action: str, data: str) -> Dict[str, Any]:
        """Multi-format decoder and hash generator."""
        data_str = data or ""
        act = (action or "").lower().strip()
        try:
            if act == "base64_decode":
                # Add padding if missing
                pad = len(data_str) % 4
                if pad:
                    data_str += "=" * (4 - pad)
                res = base64.b64decode(data_str).decode("utf-8", errors="replace")
                return {"ok": True, "result": res}

            elif act == "base64_encode":
                res = base64.b64encode(data_str.encode("utf-8")).decode("ascii")
                return {"ok": True, "result": res}

            elif act == "url_decode":
                res = urllib.parse.unquote_plus(data_str)
                return {"ok": True, "result": res}

            elif act == "url_encode":
                res = urllib.parse.quote_plus(data_str)
                return {"ok": True, "result": res}

            elif act == "hex_decode":
                clean_hex = re.sub(r"[^0-9a-fA-F]", "", data_str)
                res = bytes.fromhex(clean_hex).decode("utf-8", errors="replace")
                return {"ok": True, "result": res}

            elif act == "hex_encode":
                res = data_str.encode("utf-8").hex()
                return {"ok": True, "result": res}

            elif act == "rot13":
                import codecs
                res = codecs.decode(data_str, "rot_13")
                return {"ok": True, "result": res}

            elif act == "hash_md5":
                res = hashlib.md5(data_str.encode("utf-8")).hexdigest()
                return {"ok": True, "result": res}

            elif act == "hash_sha256":
                res = hashlib.sha256(data_str.encode("utf-8")).hexdigest()
                return {"ok": True, "result": res}

            elif act == "jwt_decode":
                parts = data_str.split(".")
                if len(parts) < 2:
                    return {"ok": False, "error": "Неверный формат JWT (ожидается 3 части через точку)"}
                
                def _b64_url_decode(s):
                    pad = len(s) % 4
                    if pad:
                        s += "=" * (4 - pad)
                    return base64.urlsafe_b64decode(s).decode("utf-8", errors="replace")

                header = json.loads(_b64_url_decode(parts[0]))
                payload = json.loads(_b64_url_decode(parts[1]))
                formatted = json.dumps({"header": header, "payload": payload}, indent=2, ensure_ascii=False)
                return {"ok": True, "result": formatted}

            elif act == "binary_encode":
                res = " ".join(format(ord(c), "08b") for c in data_str)
                return {"ok": True, "result": res}

            elif act == "binary_decode":
                bin_parts = [b for b in re.split(r"\s+", data_str) if b]
                chars = [chr(int(b, 2)) for b in bin_parts if all(c in "01" for c in b)]
                return {"ok": True, "result": "".join(chars)}

            return {"ok": False, "error": f"Неизвестное действие декодера: {action}"}
        except Exception as e:
            return {"ok": False, "error": f"Ошибка преобразования: {str(e)}"}

    @staticmethod
    async def probe_website(url: str) -> Dict[str, Any]:
        """Probes a remote website for SSL, server headers, and security posture."""
        url = url.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "https://" + url

        if not is_safe_url(url):
            return {"ok": False, "error": "Запрещенный адрес (блокировка SSRF/внутренняя сеть)."}

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CyberMultitoolProbe/3.0"})
                elapsed_ms = round((time.perf_counter() - start_time) * 1000)

                headers = dict(resp.headers)
                sec_checks = {
                    "hsts": "strict-transport-security" in headers,
                    "csp": "content-security-policy" in headers,
                    "x_frame_options": "x-frame-options" in headers,
                    "x_content_type": "x-content-type-options" in headers,
                    "referrer_policy": "referrer-policy" in headers,
                }
                
                sec_score = sum(1 for v in sec_checks.values() if v)
                rating = "Отличная" if sec_score >= 4 else ("Умеренная" if sec_score >= 2 else "Низкая")

                return {
                    "ok": True,
                    "url": str(resp.url),
                    "status_code": resp.status_code,
                    "latency_ms": elapsed_ms,
                    "server": headers.get("server", "Скрыт / Cloudflare"),
                    "content_type": headers.get("content-type", "N/A"),
                    "is_https": str(resp.url).startswith("https://"),
                    "security_headers": sec_checks,
                    "security_rating": rating,
                    "score": f"{sec_score}/5",
                }
        except Exception as e:
            return {"ok": False, "error": f"Не удалось подключиться к сайту: {str(e)}"}

    @staticmethod
    def generate_qr(text: str) -> bytes:
        """Generates high quality QR code as PNG image bytes."""
        text = (text or "").strip()[:2048]
        if not text:
            text = "Cyber Multitool"

        if qrcode is None:
            # Fallback placeholder 1x1 png if qrcode module missing
            return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=3,
        )
        qr.add_data(text)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()


# =====================================================================
# 4. AI PRODUCTIVITY & SUMMARY ENGINE
# =====================================================================

class AIProductivity:
    @staticmethod
    async def summarize_page_or_text(target: str) -> Dict[str, Any]:
        """Extracts readable content from URL or summarizes given text."""
        target = (target or "").strip()
        if not target:
            return {"ok": False, "error": "Пустой текст для анализа"}

        extracted_text = target
        title = "Анализ текста"

        if target.startswith("http://") or target.startswith("https://"):
            if not is_safe_url(target):
                return {"ok": False, "error": "Адрес заблокирован (защита SSRF)"}

            try:
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    resp = await client.get(target, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CyberReader/2.0"})
                    if resp.status_code != 200:
                        return {"ok": False, "error": f"Сайт вернул код {resp.status_code}"}

                    soup = BeautifulSoup(resp.text, "html.parser")
                    if soup.title and soup.title.string:
                        title = soup.title.string.strip()

                    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                        tag.decompose()

                    paragraphs = [p.get_text().strip() for p in soup.find_all("p") if len(p.get_text().strip()) > 40]
                    extracted_text = " ".join(paragraphs)
            except Exception as e:
                return {"ok": False, "error": f"Сбой парсинга страницы: {str(e)}"}

        if not extracted_text:
            return {"ok": False, "error": "Не удалось извлечь содержательный текст"}

        # Text analytics
        words = extracted_text.split()
        word_count = len(words)
        reading_time_min = max(1, round(word_count / 180))

        # Extractive bullet point summarizer
        sentences = re.split(r"(?<=[.!?])\s+", extracted_text)
        key_sentences = [s.strip() for s in sentences if len(s.strip()) > 30 and not s.strip().startswith("http")][:5]

        return {
            "ok": True,
            "title": title[:100],
            "stats": {
                "words": word_count,
                "reading_time_min": reading_time_min,
                "sentences_count": len(sentences),
            },
            "key_points": key_sentences,
            "summary_preview": " ".join(key_sentences[:3]) if key_sentences else extracted_text[:400],
        }


# =====================================================================
# 5. WEATHER (open-meteo, бесплатный без ключей)
# =====================================================================

class WeatherService:
    WMO_CODES = {
        0: "Ясно ☀️", 1: "Малооблачно 🌤", 2: "Переменная облачность ⛅", 3: "Пасмурно ☁️",
        45: "Туман 🌫", 48: "Изморозь 🌫",
        51: "Морось 🌦", 53: "Морось 🌦", 55: "Сильная морось 🌧",
        61: "Дождь 🌧", 63: "Дождь 🌧", 65: "Сильный дождь 🌧",
        66: "Ледяной дождь 🧊", 67: "Ледяной дождь 🧊",
        71: "Снег ❄️", 73: "Снег ❄️", 75: "Сильный снег ❄️", 77: "Снежинки ❄️",
        80: "Ливень 🌦", 81: "Ливень 🌦", 82: "Сильный ливень 🌊",
        85: "Снегопад 🌨", 86: "Снегопад 🌨",
        95: "Гроза ⛈", 96: "Гроза с градом ⛈", 99: "Гроза с градом ⛈",
    }

    @classmethod
    async def get(cls, city: str) -> Dict[str, Any]:
        city = (city or "").strip()[:80]
        if not city:
            return {"ok": False, "error": "Укажите город: /weather Москва"}
        try:
            async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": _USER_AGENT}) as client:
                # 1. геокодинг города
                r = await client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": city, "count": 1, "language": "ru"},
                )
                if r.status_code != 200:
                    return {"ok": False, "error": "Сервис погоды недоступен"}
                results = r.json().get("results") or []
                if not results:
                    return {"ok": False, "error": f"Город «{city}» не найден"}
                loc = results[0]
                lat, lon = loc["latitude"], loc["longitude"]

                # 2. прогноз
                r = await client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": lat, "longitude": lon,
                        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                                   "wind_speed_10m,weather_code",
                        "daily": "temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max",
                        "timezone": "auto", "forecast_days": 4,
                    },
                )
                if r.status_code != 200:
                    return {"ok": False, "error": "Не удалось получить прогноз"}
                d = r.json()
                cur = d.get("current", {})
                daily = d.get("daily", {})

                days = []
                for i in range(min(4, len(daily.get("time", [])))):
                    code = daily["weather_code"][i]
                    days.append({
                        "date": daily["time"][i],
                        "desc": cls.WMO_CODES.get(code, f"Код {code}"),
                        "temp_max": daily["temperature_2m_max"][i],
                        "temp_min": daily["temperature_2m_min"][i],
                        "precip": (daily.get("precipitation_probability_max") or [None] * 4)[i],
                    })

                return {
                    "ok": True,
                    "city": loc.get("name", city),
                    "country": loc.get("country", ""),
                    "timezone": d.get("timezone", ""),
                    "current": {
                        "temp": cur.get("temperature_2m"),
                        "feels": cur.get("apparent_temperature"),
                        "humidity": cur.get("relative_humidity_2m"),
                        "wind": cur.get("wind_speed_10m"),
                        "desc": cls.WMO_CODES.get(cur.get("weather_code", 0), "—"),
                    },
                    "days": days,
                }
        except Exception as e:
            return {"ok": False, "error": f"Сбой сервиса погоды: {str(e)[:150]}"}


# =====================================================================
# 6. CURRENCY (open.er-api.com, бесплатный без ключей)
# =====================================================================

class CurrencyService:
    CACHE_FILE = Path(os.getenv("DATA_DIR", "data")) / "rates_cache.json"
    CACHE_TTL = 3600  # 1 час
    _cache: Optional[Dict[str, Any]] = None

    @classmethod
    async def _rates(cls) -> Dict[str, Any]:
        # кэш в памяти + файл (переживает рестарт)
        if cls._cache and time.time() - cls._cache.get("_ts", 0) < cls.CACHE_TTL:
            return cls._cache
        try:
            if cls.CACHE_FILE.exists():
                file_cache = json.loads(cls.CACHE_FILE.read_text(encoding="utf-8"))
                if time.time() - file_cache.get("_ts", 0) < cls.CACHE_TTL:
                    cls._cache = file_cache
                    return file_cache
        except Exception:
            pass
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get("https://open.er-api.com/v6/latest/USD")
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            data = r.json()
            if data.get("result") != "success":
                raise RuntimeError("API error")
            cache = {"_ts": time.time(), "base": "USD", "rates": data.get("rates", {})}
            cls._cache = cache
            try:
                cls.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                cls.CACHE_FILE.write_text(json.dumps(cache), encoding="utf-8")
            except Exception:
                pass
            return cache

    @classmethod
    async def popular(cls) -> Dict[str, Any]:
        """Курсы популярных валют (база USD)."""
        try:
            cache = await cls._rates()
            rates = cache["rates"]
            want = ["RUB", "UAH", "EUR", "BYN", "CNY", "GBP", "PLN", "TRY", "KZT"]
            out = [
                {"code": code, "per_usd": rates[code]}
                for code in want if code in rates
            ]
            return {"ok": True, "base": "USD", "updated": int(cache["_ts"]), "currencies": out}
        except Exception as e:
            return {"ok": False, "error": f"Курсы недоступны: {str(e)[:120]}"}

    @classmethod
    async def convert(cls, amount: float, from_cur: str, to_cur: str) -> Dict[str, Any]:
        from_cur = (from_cur or "").strip().upper()[:5]
        to_cur = (to_cur or "").strip().upper()[:5]
        if not from_cur or not to_cur:
            return {"ok": False, "error": "Использование: /cur 100 USD RUB"}
        if not (0 < amount < 10**12):
            return {"ok": False, "error": "Некорректная сумма"}
        try:
            cache = await cls._rates()
            rates = cache["rates"]
            if from_cur not in rates or to_cur not in rates:
                bad = from_cur if from_cur not in rates else to_cur
                return {"ok": False, "error": f"Валюта {bad} не найдена. Примеры: USD, EUR, RUB, UAH"}
            result = amount / rates[from_cur] * rates[to_cur]
            return {
                "ok": True,
                "amount": amount,
                "from": from_cur,
                "to": to_cur,
                "result": round(result, 4),
                "rate": round(rates[to_cur] / rates[from_cur], 6),
                "updated": int(cache["_ts"]),
            }
        except Exception as e:
            return {"ok": False, "error": f"Конвертер недоступен: {str(e)[:120]}"}


# =====================================================================
# 7. PASSWORD BREACH CHECK (HIBP k-anonimity — пароль не покидает устройство)
# =====================================================================

class PasswordAudit:
    @classmethod
    async def check(cls, password: str) -> Dict[str, Any]:
        password = password or ""
        if len(password) < 4:
            return {"ok": False, "error": "Пароль слишком короткий (минимум 4 символа)"}
        if len(password) > 128:
            return {"ok": False, "error": "Пароль слишком длинный (максимум 128)"}
        try:
            sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
            prefix, suffix = sha1[:5], sha1[5:]
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(f"https://api.pwnedpasswords.com/range/{prefix}")
                if r.status_code != 200:
                    return {"ok": False, "error": f"Сервис проверки недоступен (HTTP {r.status_code})"}
            count = 0
            for line in r.text.splitlines():
                parts = line.strip().split(":")
                if len(parts) == 2 and parts[0] == suffix:
                    count = int(parts[1])
                    break
            # оценка стойкости (по энтропии)
            pool = 0
            if re.search(r"[a-z]", password): pool += 26
            if re.search(r"[A-Z]", password): pool += 26
            if re.search(r"\d", password): pool += 10
            if re.search(r"[^A-Za-z0-9]", password): pool += 32
            entropy = round(len(password) * math.log2(pool), 1) if pool else 0

            return {
                "ok": True,
                "breaches": count,
                "pwned": count > 0,
                "entropy_bits": entropy,
                "length": len(password),
                "note": "Проверка по принципу k-анонимности: на сервер ушёл только 5-символьный префикс SHA-1.",
            }
        except Exception as e:
            return {"ok": False, "error": f"Сбой проверки: {str(e)[:150]}"}


# =====================================================================
# 8. URL SHORTENER (собственные короткие ссылки, хранение в data/links.json)
# =====================================================================

class LinkShortener:
    STORE_FILE = Path(os.getenv("DATA_DIR", "data")) / "links.json"
    CODE_LEN = 6

    @classmethod
    def _load(cls) -> Dict[str, Any]:
        try:
            if cls.STORE_FILE.exists():
                return json.loads(cls.STORE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    @classmethod
    def _save(cls, data: Dict[str, Any]) -> None:
        try:
            cls.STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
            cls.STORE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"shortener save: {e}")

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        try:
            p = urllib.parse.urlparse(url.strip())
            return p.scheme in ("http", "https") and bool(p.hostname)
        except Exception:
            return False

    @classmethod
    async def shorten(cls, url: str, base_url: str = "") -> Dict[str, Any]:
        url = (url or "").strip()
        if not cls._is_valid_url(url):
            return {"ok": False, "error": "Нужна корректная ссылка http(s)://..."}
        if len(url) > 2048:
            return {"ok": False, "error": "Ссылка слишком длинная (макс. 2048)"}
        store = cls._load()
        # переиспользуем существующий код для той же ссылки
        code = None
        for c, meta in store.items():
            if meta.get("url") == url:
                code = c
                break
        if code is None:
            alphabet = string.ascii_letters + string.digits
            for _ in range(8):
                candidate = "".join(secrets.choice(alphabet) for _ in range(cls.CODE_LEN))
                if candidate not in store:
                    code = candidate
                    break
            if code is None:
                return {"ok": False, "error": "Не удалось сгенерировать код"}
            store[code] = {"url": url, "created": int(time.time()), "hits": 0}
            cls._save(store)
        base = (base_url or "").rstrip("/")
        short = f"{base}/s/{code}" if base else f"/s/{code}"
        return {"ok": True, "code": code, "short_url": short, "original": url}

    @classmethod
    def resolve(cls, code: str) -> Optional[str]:
        if not re.fullmatch(r"[A-Za-z0-9]{4,12}", code or ""):
            return None
        store = cls._load()
        meta = store.get(code)
        if not meta:
            return None
        meta["hits"] = int(meta.get("hits", 0)) + 1
        store[code] = meta
        cls._save(store)
        return meta.get("url")

    @classmethod
    def stats(cls) -> Dict[str, Any]:
        store = cls._load()
        return {
            "ok": True,
            "total_links": len(store),
            "total_hits": sum(int(m.get("hits", 0)) for m in store.values()),
        }


# =====================================================================
# 9. WI-FI QR (генерация QR с параметрами Wi-Fi сети)
# =====================================================================

class WifiQr:
    @staticmethod
    def generate(ssid: str, password: str, encryption: str = "WPA") -> Dict[str, Any]:
        ssid = (ssid or "").strip()
        password = password or ""
        if not ssid:
            return {"ok": False, "error": "Укажите имя сети (SSID): /wifi МояСеть пароль"}
        if encryption not in ("WPA", "WEP", "nopass"):
            encryption = "WPA"
        if encryption != "nopass" and not password:
            return {"ok": False, "error": "Укажите пароль или используйте encryption=nopass"}

        def esc(s: str) -> str:
            return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace(":", "\\:")

        if encryption == "nopass":
            payload = f"WIFI:T:nopass;S:{esc(ssid)};;"
        else:
            payload = f"WIFI:T:{encryption};S:{esc(ssid)};P:{esc(password)};;"

        if qrcode is None:
            return {"ok": False, "error": "Модуль qrcode не установлен"}
        qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
                           box_size=10, border=3)
        qr.add_data(payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return {"ok": True, "png": buf.getvalue(), "ssid": ssid, "encryption": encryption}


# =====================================================================
# 10. IMAGE COMPRESSOR (Pillow — сжатие фото перед отправкой)
# =====================================================================

class ImageCompressor:
    MAX_SIDE = 2560          # не ужимать мельче, чем этот размер
    QUALITY = 78

    @classmethod
    def compress(cls, data: bytes, quality: Optional[int] = None) -> Dict[str, Any]:
        if Image is None:
            return {"ok": False, "error": "Модуль Pillow не установлен"}
        if not data:
            return {"ok": False, "error": "Пустой файл"}
        if len(data) > 20 * 1024 * 1024:
            return {"ok": False, "error": "Файл больше 20 МБ"}
        quality = max(20, min(95, quality or cls.QUALITY))
        try:
            img = Image.open(io.BytesIO(data))
            img.load()
            original_size = len(data)
            fmt = (img.format or "").upper()
            # анимацию GIF не трогаем
            if fmt == "GIF":
                return {"ok": True, "png": data, "original_size": original_size,
                        "new_size": original_size, "saved_pct": 0, "format": "GIF"}

            if img.mode in ("RGBA", "P", "LA"):
                # перекодируем в RGB (JPEG не поддерживает прозрачность)
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                mask = img.split()[-1] if img.mode in ("RGBA", "LA") else None
                background.paste(img, mask=mask)
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            w, h = img.size
            if max(w, h) > cls.MAX_SIDE:
                ratio = cls.MAX_SIDE / max(w, h)
                img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

            out = io.BytesIO()
            img.save(out, format="JPEG", quality=quality, optimize=True, progressive=True)
            result = out.getvalue()
            saved = max(0, round((1 - len(result) / original_size) * 100, 1))
            return {
                "ok": True,
                "png": result,
                "original_size": original_size,
                "new_size": len(result),
                "saved_pct": saved,
                "dimensions": f"{img.size[0]}x{img.size[1]}",
                "format": "JPEG",
            }
        except Exception as e:
            return {"ok": False, "error": f"Не удалось обработать изображение: {str(e)[:150]}"}


# =====================================================================
# 11. UNIT CONVERTER (офлайн-конвертер единиц)
# =====================================================================

class UnitConverter:
    # category → {unit: factor (относительно базовой единицы)}
    UNITS: Dict[str, Dict[str, float]] = {
        "length": {  # база: метр
            "mm": 0.001, "cm": 0.01, "m": 1, "km": 1000,
            "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344,
        },
        "weight": {  # база: грамм
            "mg": 0.001, "g": 1, "kg": 1000, "t": 1_000_000,
            "oz": 28.3495, "lb": 453.592,
        },
        "data": {  # база: байт
            "b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3, "tb": 1024**4,
        },
        "speed": {  # база: км/ч
            "kmh": 1, "mph": 1.609344, "ms": 3.6, "kn": 1.852,
        },
        "area": {  # база: кв. метр
            "m2": 1, "km2": 1_000_000, "ft2": 0.092903, "acre": 4046.86, "ha": 10_000,
        },
        "volume": {  # база: литр
            "ml": 0.001, "l": 1, "gal": 3.78541, "pt": 0.473176, "cup": 0.236588,
        },
    }
    TEMPERATURES = ("c", "f", "k")
    ALIASES = {
        "м": "m", "км": "km", "см": "cm", "мм": "mm", "кг": "kg", "г": "g",
        "мили": "mi", "миля": "mi", "фут": "ft", "дюйм": "in",
        "килобайт": "kb", "мегабайт": "mb", "гигабайт": "gb", "терабайт": "tb",
        "км/ч": "kmh", "м/с": "ms", "метр": "m",
        "°c": "c", "°f": "f", "цельсий": "c", "фаренгейт": "f",
    }

    @classmethod
    def _find_unit(cls, unit: str) -> Optional[tuple]:
        u = unit.lower().strip()
        u = cls.ALIASES.get(u, u)
        if u in cls.TEMPERATURES:
            return ("temperature", u)
        for cat, table in cls.UNITS.items():
            if u in table:
                return cat, u
        return None

    @staticmethod
    def _convert_temperature(value: float, src: str, dst: str) -> float:
        # → °C
        c = value if src == "c" else (value - 32) * 5 / 9 if src == "f" else value - 273.15
        # °C → цель
        if dst == "c":
            return c
        if dst == "f":
            return c * 9 / 5 + 32
        return c + 273.15

    @classmethod
    def convert(cls, value: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
        if not (-(10**12) <= value < 10**15):
            return {"ok": False, "error": "Некорректное значение"}
        src = cls._find_unit(from_unit or "")
        dst = cls._find_unit(to_unit or "")
        if not src:
            return {"ok": False,
                    "error": f"Единица «{from_unit}» не распознана. Примеры: km, m, kg, mi, gb, kmh, c, f"}
        if not dst:
            return {"ok": False,
                    "error": f"Единица «{to_unit}» не распознана. Примеры: km, m, kg, mi, gb, kmh, c, f"}
        if src[0] != dst[0]:
            return {"ok": False, "error": "Единицы разного типа (длина/вес/температура и т.д.)"}

        if src[0] == "temperature":
            result = cls._convert_temperature(value, src[1], dst[1])
        else:
            result = value * cls.UNITS[src[0]][src[1]] / cls.UNITS[src[0]][dst[1]]

        return {
            "ok": True,
            "value": value,
            "from": from_unit,
            "to": to_unit,
            "result": round(result, 6),
        }

    @classmethod
    def categories(cls) -> Dict[str, List[str]]:
        out = {cat: sorted(table.keys()) for cat, table in cls.UNITS.items()}
        out["temperature"] = list(cls.TEMPERATURES)
        return out






