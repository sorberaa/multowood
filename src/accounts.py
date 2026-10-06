"""
Multiwood Accounts — единая система аккаунтов для Telegram-бота и FastAPI-веба.

Хранение: DATA_DIR/users.json (атомарная запись через tmp-файл + os.replace).
Модель пользователя:
    {
      "tg_id": "5233450569", "username": "john", "first_name": "John",
      "nickname": "ShadowAgent",   # отображаемый ник (меняется пользователем)
      "role": "user" | "vip" | "admin", "banned": false,
      "xp": 120, "level": 4,       # уровень вычисляется из xp
      "downloads": 12, "mails": 3, "scans": 7,
      "daily_streak": 3, "last_daily": "2026-02-10",
      "created_at": "...", "last_seen": "..."
    }

Правила:
  * роль admin вычисляется автоматически по ADMIN_CHAT_ID;
  * бан-флаг блокирует бота (middleware) и веб-эндпоинты;
  * XP: скачивание +2, письмо +1, скан +3, ежедневный бонус +15.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("accounts")

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
USERS_FILE = DATA_DIR / "users.json"

ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "5233450569")

XP_PER_LEVEL = 20          # XP на уровень
XP_DOWNLOAD = 2
XP_MAIL = 1
XP_SCAN = 3
XP_DAILY = 15


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def level_from_xp(xp: int) -> int:
    return max(1, xp // XP_PER_LEVEL + 1)


def xp_for_next_level(level: int) -> int:
    return level * XP_PER_LEVEL


def load_users() -> Dict[str, Any]:
    if not USERS_FILE.exists():
        return {}
    try:
        data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.error(f"load_users: {e}")
        bak = USERS_FILE.with_suffix(".json.bak")
        try:
            if bak.exists():
                return json.loads(bak.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}


def save_users(users: Dict[str, Any]) -> None:
    """Атомарная запись: tmp-файл в той же папке + os.replace (не рвёт чтение)."""
    try:
        USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            prefix="users_", suffix=".json", dir=str(USERS_FILE.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(users, f, ensure_ascii=False, indent=2)
            if USERS_FILE.exists():
                try:
                    USERS_FILE.replace(USERS_FILE.with_suffix(".json.bak"))
                except Exception:
                    pass
            os.replace(tmp_path, USERS_FILE)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
    except Exception as e:
        logger.error(f"save_users: {e}")


def normalize_id(tg_id: Any) -> str:
    return str(tg_id).strip()

def register_user(
    tg_id: Any,
    username: str = "",
    first_name: str = "",
    nickname: str = "",
    role: Optional[str] = None,
) -> Dict[str, Any]:
    """Создаёт или обновляет профиль. Возвращает итоговый профиль."""
    tg_id = normalize_id(tg_id)
    if not tg_id:
        return {}
    users = load_users()
    u = users.get(tg_id) or _blank(tg_id)
    if username:
        u["username"] = username.lstrip("@")[:64]
    if first_name:
        u["first_name"] = first_name[:64]
    if nickname and not u.get("nickname"):
        u["nickname"] = nickname[:32]
    # роль admin — только по ADMIN_CHAT_ID, независимо от сохранённой
    if is_admin_id(tg_id):
        u["role"] = "admin"
    elif role and u.get("role") != "admin":
        u["role"] = role if role in ("user", "vip") else u.get("role", "user")
    u["last_seen"] = _now_iso()
    u["level"] = level_from_xp(int(u.get("xp", 0)))
    users[tg_id] = u
    save_users(users)
    return u


def get_profile(tg_id: Any) -> Optional[Dict[str, Any]]:
    tg_id = normalize_id(tg_id)
    if not tg_id:
        return None
    return load_users().get(tg_id)


def update_profile(tg_id: Any, **fields: Any) -> Optional[Dict[str, Any]]:
    tg_id = normalize_id(tg_id)
    users = load_users()
    u = users.get(tg_id)
    if u is None:
        return None
    allowed = {
        "username", "first_name", "nickname", "role", "banned",
        "xp", "downloads", "mails", "scans", "daily_streak", "last_daily",
    }
    for k, v in fields.items():
        if k in allowed:
            u[k] = v
    # защита: admin-роль нельзя снять, админа нельзя забанить
    if is_admin_id(tg_id):
        u["role"] = "admin"
        u["banned"] = False
    u["level"] = level_from_xp(int(u.get("xp", 0)))
    u["last_seen"] = _now_iso()
    users[tg_id] = u
    save_users(users)
    return u


def is_banned(tg_id: Any) -> bool:
    p = get_profile(tg_id)
    return bool(p and p.get("banned"))


def set_banned(tg_id: Any, banned: bool) -> Optional[Dict[str, Any]]:
    tg_id = normalize_id(tg_id)
    if is_admin_id(tg_id):
        return None  # админа забанить нельзя
    return update_profile(tg_id, banned=bool(banned))


def add_xp(tg_id: Any, amount: int) -> Optional[Dict[str, Any]]:
    tg_id = normalize_id(tg_id)
    p = get_profile(tg_id)
    if p is None:
        p = register_user(tg_id)
        if not p:
            return None
    xp = int(p.get("xp", 0)) + int(amount)
    return update_profile(tg_id, xp=max(0, xp))


def bump_counter(tg_id: Any, field: str) -> Optional[Dict[str, Any]]:
    """field: downloads | mails | scans"""
    tg_id = normalize_id(tg_id)
    p = get_profile(tg_id)
    if p is None:
        p = register_user(tg_id)
        if not p:
            return None
    val = int(p.get(field, 0)) + 1
    return update_profile(tg_id, **{field: val})


def claim_daily(tg_id: Any) -> Dict[str, Any]:
    """Ежедневный бонус. Возвращает {ok, xp_gained, streak, already, profile}."""
    tg_id = normalize_id(tg_id)
    p = get_profile(tg_id) or register_user(tg_id)
    if not p:
        return {"ok": False, "error": "Аккаунт не найден"}
    today = date.today().isoformat()
    if p.get("last_daily") == today:
        return {
            "ok": True, "already": True, "xp_gained": 0,
            "streak": int(p.get("daily_streak", 0)), "profile": p,
        }
    yesterday = date.fromordinal(date.today().toordinal() - 1).isoformat()
    streak = int(p.get("daily_streak", 0))
    streak = streak + 1 if p.get("last_daily") == yesterday else 1
    p = update_profile(tg_id, last_daily=today, daily_streak=streak,
                       xp=int(p.get("xp", 0)) + XP_DAILY)
    return {
        "ok": True, "already": False, "xp_gained": XP_DAILY,
        "streak": streak, "profile": p,
    }


def list_users(limit: int = 500, offset: int = 0) -> List[Dict[str, Any]]:
    users = load_users()
    items = sorted(users.values(), key=lambda u: int(u.get("xp", 0)), reverse=True)
    return items[offset:offset + limit]


def leaderboard(top_n: int = 10) -> List[Dict[str, Any]]:
    return list_users(limit=top_n)


def admin_stats() -> Dict[str, Any]:
    users = load_users()
    total = len(users)
    banned = sum(1 for u in users.values() if u.get("banned"))
    vip = sum(1 for u in users.values() if u.get("role") == "vip")
    downloads = sum(int(u.get("downloads", 0)) for u in users.values())
    scans = sum(int(u.get("scans", 0)) for u in users.values())
    today = date.today().isoformat()
    active_today = sum(
        1 for u in users.values()
        if str(u.get("last_seen", "")).startswith(today)
    )
    return {
        "total_users": total,
        "banned": banned,
        "vip": vip,
        "total_downloads": downloads,
        "total_scans": scans,
        "active_today": active_today,
    }


def broadcaster_targets() -> List[str]:
    """ID получателей рассылки: только цифровые, не забаненные, + админ."""
    users = load_users()
    ids = [
        tid for tid, u in users.items()
        if tid.isdigit() and not u.get("banned")
    ]
    if ADMIN_CHAT_ID and str(ADMIN_CHAT_ID) not in ids:
        ids.append(str(ADMIN_CHAT_ID))
    return ids



def is_admin_id(tg_id: Any) -> bool:
    return bool(ADMIN_CHAT_ID) and normalize_id(tg_id) == normalize_id(ADMIN_CHAT_ID)


def _blank(tg_id: str) -> Dict[str, Any]:
    return {
        "tg_id": tg_id,
        "username": "",
        "first_name": "",
        "nickname": "",
        "role": "admin" if is_admin_id(tg_id) else "user",
        "banned": False,
        "xp": 0,
        "level": 1,
        "downloads": 0,
        "mails": 0,
        "scans": 0,
        "daily_streak": 0,
        "last_daily": "",
        "created_at": _now_iso(),
        "last_seen": _now_iso(),
    }
