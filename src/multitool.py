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
# 2. TEMP MAIL SERVICE (1SECMAIL PUBLIC API INTEGRATION)
# =====================================================================

class TempMailService:
    API_BASE = "https://www.1secmail.com/api/v1/"

    @classmethod
    async def create_inbox(cls) -> Dict[str, Any]:
        """Creates a temporary disposable mailbox."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(f"{cls.API_BASE}?action=genRandomMailbox&count=1")
                if res.status_code == 200:
                    emails = res.json()
                    if emails and isinstance(emails, list):
                        email = emails[0]
                        return {
                            "ok": True,
                            "email": email,
                            "token": email,  # 1secmail uses full email as token identifier
                        }
            return {"ok": False, "error": "Не удалось сгенерировать адрес почты"}
        except Exception as e:
            logger.error(f"TempMail create error: {e}")
            return {"ok": False, "error": f"Сбой сервиса почты: {str(e)}"}

    @classmethod
    async def get_messages(cls, token: str) -> Dict[str, Any]:
        """Fetches inbox message list for given email token."""
        try:
            if "@" not in token:
                return {"ok": False, "error": "Неверный формат токена почты"}
            login, domain = token.split("@", 1)

            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(f"{cls.API_BASE}?action=getMessages&login={urllib.parse.quote(login)}&domain={urllib.parse.quote(domain)}")
                if res.status_code == 200:
                    messages = res.json()
                    return {"ok": True, "messages": messages if isinstance(messages, list) else []}
            return {"ok": False, "error": f"Ошибка сервера почты: HTTP {res.status_code}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @classmethod
    async def get_message_detail(cls, token: str, message_id: str) -> Dict[str, Any]:
        """Reads detailed message body."""
        try:
            if "@" not in token:
                return {"ok": False, "error": "Неверный формат токена почты"}
            login, domain = token.split("@", 1)

            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    f"{cls.API_BASE}?action=readMessage&login={urllib.parse.quote(login)}&domain={urllib.parse.quote(domain)}&id={urllib.parse.quote(str(message_id))}"
                )
                if res.status_code == 200:
                    detail = res.json()
                    return {"ok": True, "message": detail}
            return {"ok": False, "error": f"Письмо не найдено: HTTP {res.status_code}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}


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

