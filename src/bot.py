"""
Multiwood Telegram Bot - Smart Mobile Multitool
Fast social media downloader, mobile utilities, OSINT recon and Telegram Mini App integration.
"""

import asyncio
import html
import json
import logging
import os
import urllib.parse
from pathlib import Path

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    WebAppInfo,
    BotCommand,
)
from dotenv import load_dotenv

import accounts
from multitool import MediaDownloader, TempMailService, DevSecurityTools

load_dotenv("/app/config/.env")
load_dotenv("config/.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
DOMAIN = os.getenv("DOMAIN", "https://multowood.onrender.com").rstrip("/")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "5233450569")
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Память для отложенных URL (не влезают в 64-байтный callback_data)
_PENDING_URLS: dict[int, str] = {}


def is_admin(user_id: int) -> bool:
    return accounts.is_admin_id(user_id)


def get_webapp_url() -> str:
    sep = "&" if "?" in DOMAIN else "?"
    return f"{DOMAIN}{sep}v=5.0_accounts"


def get_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚡ Открыть Мультитул (Mini App)",
                    web_app=WebAppInfo(url=get_webapp_url())
                )
            ],
            [
                InlineKeyboardButton(text="📬 Временная почта", callback_data="btn_quick_mail"),
                InlineKeyboardButton(text="🔐 Новый пароль", callback_data="btn_quick_pass"),
            ],
            [
                InlineKeyboardButton(text="👤 Мой профиль", callback_data="btn_profile"),
                InlineKeyboardButton(text="🏆 Топ пользователей", callback_data="btn_top"),
            ],
            [
                InlineKeyboardButton(text="ℹ️ Как скачать видео", callback_data="btn_help_dl")
            ]
        ]
    )


def register_or_update(message: types.Message) -> bool:
    """Регистрирует/обновляет аккаунт. True — если пользователь забанен."""
    user = message.from_user
    if not user:
        return False
    if accounts.get_profile(user.id) is None:
        accounts.register_user(
            user.id,
            username=user.username or "",
            first_name=user.first_name or "",
        )
    else:
        accounts.update_profile(
            user.id,
            username=user.username or "",
            first_name=user.first_name or "",
        )
    return accounts.is_banned(user.id)



# =====================================================================
# BASIC COMMANDS
# =====================================================================

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    if register_or_update(message):
        await message.answer("⛔ Ваш аккаунт заблокирован администратором.")
        return

    user_name = message.from_user.first_name or "друг"
    admin_hint = "\n\n👑 <b>Админ-панель:</b> <code>/admin</code>" if is_admin(message.from_user.id) else ""
    p = accounts.get_profile(message.from_user.id) or {}
    level = p.get("level", 1)

    text = (
        f"👋 <b>Привет, {html.escape(user_name)}!</b> Уровень аккаунта: <b>{level}</b>\n"
        f"Добро пожаловать в <b>Multiwood</b> — твой персональный мультитул для смартфона.\n\n"
        f"📥 <b>СКАЧИВАНИЕ ИЗ СОЦСЕТЕЙ БЕЗ ВОДЯНЫХ ЗНАКОВ:</b>\n"
        f"Просто <b>отправь ссылку</b> в чат (TikTok, Instagram Reels, YouTube Shorts, X, Pinterest, VK) — и бот пришлёт чистое видео или аудио!\n\n"
        f"🔍 <b>OSINT-РАЗВЕДКА (учебная):</b>\n"
        f"<code>/username ник</code> — поиск аккаунтов по 60+ сайтам\n"
        f"<code>/phone номер</code> · <code>/ip адрес</code> · <code>/domain сайт</code> · <code>/dorks запрос</code>\n\n"
        f"🛠 <b>МОБИЛЬНЫЕ УТИЛИТЫ:</b>\n"
        f"Временная почта, генератор паролей, QR-коды, очистка ссылок от трекеров и AI-выжимка.\n\n"
        f"🎮 <b>ПРОГРЕСС:</b> <code>/daily</code> — ежедневный бонус XP, <code>/top</code> — таблица лидеров, <code>/profile</code> — твой профиль.\n\n"
        f"⚡ <i>Нажми кнопку ниже, чтобы открыть полноэкранный Mini App:</i>"
        f"{admin_hint}"
    )
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="HTML")


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "📖 <b>Команды Multiwood:</b>\n\n"
        "📥 <b>Скачивание</b>\n"
        "— просто пришлите ссылку в чат или <code>/dl ссылка</code>\n\n"
        "🎮 <b>Аккаунт</b>\n"
        "<code>/profile</code> — профиль, уровень и статистика\n"
        "<code>/nick имя</code> — сменить отображаемый ник\n"
        "<code>/daily</code> — ежедневный бонус XP\n"
        "<code>/top</code> — таблица лидеров\n\n"
        "🔍 <b>OSINT (учебный, только публичные данные)</b>\n"
        "<code>/username ник</code> — поиск аккаунтов на сайтах\n"
        "<code>/phone +7...</code> — оператор и регион номера\n"
        "<code>/ip 1.1.1.1</code> — геолокация IP\n"
        "<code>/domain site.com</code> — DNS и HTTP-анализ\n"
        "<code>/dorks запрос</code> — Google-dorks для поиска\n\n"
        "🛠 <b>Утилиты</b>\n"
        "<code>/mail</code> — временная почта · <code>/pass [длина]</code> — пароль\n"
        "<code>/qr текст</code> — QR-код · <code>/clean ссылка</code> — убрать трекеры\n"
        "<code>/hash текст</code> — MD5/SHA256 · <code>/sum ссылка</code> — AI-выжимка\n\n"
        "👑 <b>Админ</b>\n"
        "<code>/admin</code> — панель · <code>/visits</code> — визиты · "
        "<code>/bc текст</code> — рассылка · <code>/ban id</code> / <code>/unban id</code>\n\n"
        "⚡ <i>Или просто откройте Мультитул кнопкой ниже:</i>"
    )
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="HTML")



# =====================================================================
# MEDIA DOWNLOADER (SMART LINK SNIFFER)
# =====================================================================

async def handle_media_download(message: types.Message, url: str, extract_audio: bool = False):
    uid = message.from_user.id if message.from_user else None
    if uid and accounts.is_banned(uid):
        await message.answer("⛔ Ваш аккаунт заблокирован администратором.")
        return
    status_msg = await message.answer("⏳ <i>Подключаюсь к серверу и скачиваю без водяных знаков...</i>", parse_mode="HTML")
    try:
        res = await MediaDownloader.download_media(url, extract_audio=extract_audio)
        if not res.get("ok"):
            await status_msg.edit_text(f"❌ <b>Ошибка:</b> {html.escape(res.get('error', 'Не удалось скачать медиа'))}", parse_mode="HTML")
            return

        filepath = res.get("filepath")
        if not filepath or not os.path.exists(filepath):
            await status_msg.edit_text("❌ Ошибка: файл не найден после скачивания.")
            return

        # начисляем XP за успешное скачивание
        if uid:
            accounts.bump_counter(uid, "downloads")
            accounts.add_xp(uid, accounts.XP_DOWNLOAD)

        title = res.get("title", "Медиафайл")
        uploader = res.get("uploader", "Неизвестный автор")
        filesize = os.path.getsize(filepath)
        fmt = res.get("format", "video/mp4")
        caption = f"🎬 <b>{html.escape(title[:70])}</b>\n👤 <i>{html.escape(uploader)}</i>\n⚡ <i>Скачано через @Multiwood_bot</i>"

        # Лимит прямой отправки в Telegram Bot API — 50 МБ
        if filesize > 49 * 1024 * 1024:
            clean_url = f"{DOMAIN}/api/multitool/file?p={urllib.parse.quote(filepath)}"
            mb = round(filesize / (1024 * 1024), 1)
            kb = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="📥 Скачать на устройство напрямую", url=clean_url)]]
            )
            await status_msg.edit_text(
                f"⚠️ <b>Файл превышает 50 МБ ({mb} МБ)</b>\n"
                f"Telegram ограничивает прямую отправку ботами до 50 МБ.\n\n"
                f"Вы можете скачать файл на высокой скорости по прямой ссылке:",
                reply_markup=kb,
                parse_mode="HTML"
            )
            return

        media_input = FSInputFile(filepath)
        await status_msg.delete()

        if extract_audio or "audio" in fmt or filepath.lower().endswith((".mp3", ".m4a", ".wav")):
            await message.answer_audio(audio=media_input, caption=caption, parse_mode="HTML")
        else:
            try:
                await message.answer_video(video=media_input, caption=caption, parse_mode="HTML")
            except Exception:
                await message.answer_document(document=media_input, caption=caption, parse_mode="HTML")

        # Удаление временного файла после отправки
        try:
            os.remove(filepath)
        except Exception:
            pass

    except Exception as e:
        try:
            await status_msg.edit_text(f"❌ <b>Сбой:</b> {html.escape(str(e))}", parse_mode="HTML")
        except Exception:
            pass


@dp.message(Command("dl"))
@dp.message(Command("download"))
async def cmd_download_media(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("📥 <b>Использование:</b> <code>/dl &lt;ссылка&gt;</code>\nИли просто пришлите ссылку на видео в чат!", parse_mode="HTML")
        return
    await handle_media_download(message, parts[1].strip())


# =====================================================================
# UTILITY COMMANDS (/mail, /pass, /qr)
# =====================================================================

@dp.message(Command("mail"))
async def cmd_mail(message: types.Message):
    res = await TempMailService.create_inbox()
    if res.get("ok"):
        email = res.get("email")
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="📬 Открыть почту в Mini App", web_app=WebAppInfo(url=get_webapp_url()))]]
        )
        await message.answer(
            f"📬 <b>Ваш временный одноразовый ящик:</b>\n<code>{email}</code>\n\n"
            f"<i>Используйте для безопасной регистрации без спама. Письма можно прочитать в Mini App!</i>",
            reply_markup=kb,
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Сервис почты временно недоступен. Попробуйте через пару минут.")


@dp.message(Command("pass"))
async def cmd_pass(message: types.Message):
    parts = message.text.split()
    length = 16
    if len(parts) > 1 and parts[1].isdigit():
        length = max(8, min(40, int(parts[1])))
    pwd_res = DevSecurityTools.generate_password(length=length)
    pwd = pwd_res["password"]
    await message.answer(
        f"🔐 <b>Сгенерирован защищенный пароль:</b>\n<code>{html.escape(pwd)}</code>\n\n"
        f"🛡 <i>Энтропия: {pwd_res['entropy']} бит ({pwd_res['strength']})</i>",
        parse_mode="HTML"
    )


@dp.message(Command("qr"))
async def cmd_qr(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("📷 <b>Использование:</b> <code>/qr ваш_текст_или_ссылка</code>", parse_mode="HTML")
        return
    text = parts[1].strip()
    qr_bytes = DevSecurityTools.generate_qr(text)
    from aiogram.types import BufferedInputFile
    img_file = BufferedInputFile(qr_bytes, filename="qr.png")
    await message.answer_photo(photo=img_file, caption=f"📷 <b>QR-код готов!</b>\n<code>{html.escape(text[:60])}</code>", parse_mode="HTML")


_TRACKING_PARAMS = (
    "utm_", "fbclid", "gclid", "igsh", "igshid", "mc_cid", "mc_eid",
    "yclid", "ysclid", "_hsenc", "_hsmi", "ttclid", "twclid", "ref_src",
    "spm", "scm", "share_source", "share_medium", "share_pluto",
    "share_tag", "share_item_id", "u_code", "mibextid",
)


def _clean_url(url: str) -> str:
    """Удаляет трекер-параметры из ссылки (офлайн-фильтр)."""
    try:
        parsed = urllib.parse.urlparse(url.strip())
        if parsed.query:
            pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
            keep = [
                (k, v) for k, v in pairs
                if not any(k.lower().startswith(p) for p in _TRACKING_PARAMS)
                and k.lower() != "si"
            ]
            query = urllib.parse.urlencode(keep)
            return urllib.parse.urlunparse(parsed._replace(query=query))
        return url
    except Exception:
        return url


@dp.message(Command("clean"))
async def cmd_clean(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "🪄 <b>Использование:</b> <code>/clean https://site.com/v?id=1&amp;utm_source=tg</code>\n"
            "Уберёт UTM и другие трекеры из ссылки.",
            parse_mode="HTML",
        )
        return
    cleaned = _clean_url(parts[1])
    if cleaned == parts[1].strip():
        await message.answer("✅ Ссылка уже чистая — трекеров не найдено.")
    else:
        await message.answer(
            f"🪄 <b>Чистая ссылка:</b>\n<code>{html.escape(cleaned)}</code>",
            parse_mode="HTML",
        )


@dp.message(Command("hash"))
async def cmd_hash(message: types.Message):
    import hashlib as _hl
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("🔐 <b>Использование:</b> <code>/hash любой текст</code>", parse_mode="HTML")
        return
    data = parts[1].encode("utf-8")
    await message.answer(
        "🔐 <b>Хэши текста:</b>\n"
        f"MD5: <code>{_hl.md5(data).hexdigest()}</code>\n"
        f"SHA1: <code>{_hl.sha1(data).hexdigest()}</code>\n"
        f"SHA256: <code>{_hl.sha256(data).hexdigest()}</code>",
        parse_mode="HTML",
    )


@dp.message(Command("sum"))
async def cmd_sum(message: types.Message):
    from multitool import AIProductivity
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "🧠 <b>Использование:</b> <code>/sum https://статья</code> или <code>/sum длинный текст</code>",
            parse_mode="HTML",
        )
        return
    status = await message.answer("🧠 <i>Делаю выжимку...</i>", parse_mode="HTML")
    try:
        res = await AIProductivity.summarize_page_or_text(parts[1])
    except Exception as e:
        await status.edit_text(f"❌ Сбой анализа: {html.escape(str(e)[:150])}", parse_mode="HTML")
        return
    if not res.get("ok"):
        await status.edit_text(f"❌ {html.escape(res.get('error', 'Ошибка'))}", parse_mode="HTML")
        return
    points = "\n".join(f"• {html.escape(p)}" for p in res.get("key_points", []))
    stats = res.get("stats", {})
    text = (
        f"🧠 <b>{html.escape(str(res.get('title', 'Выжимка')))}</b>\n"
        f"Слов: {stats.get('words', '?')} · чтение ~{stats.get('reading_time_min', '?')} мин\n\n"
        f"{points or html.escape(str(res.get('summary_preview', '')))[:800]}"
    )
    await status.edit_text(text, parse_mode="HTML")



# =====================================================================
# ADMIN COMMANDS
# =====================================================================

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ только для администратора.")
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👑 Открыть Админ-панель", web_app=WebAppInfo(url=get_webapp_url()))]
        ]
    )
    await message.answer("👑 <b>Панель управления администратора Multiwood:</b>", reply_markup=kb, parse_mode="HTML")


@dp.message(Command("visits"))
async def cmd_visits(message: types.Message):
    """Последние визиты (журнал data/visitors.json)."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ только для администратора.")
        return
    try:
        vfile = DATA_DIR / "visitors.json"
        visits = json.loads(vfile.read_text(encoding="utf-8")) if vfile.exists() else []
    except Exception:
        visits = []
    if not visits:
        await message.answer("📊 Журнал визитов пуст.")
        return
    lines = [f"📊 <b>Последние визиты (всего {len(visits)}):</b>\n"]
    for v in visits[-15:][::-1]:
        lines.append(
            f"• <code>{html.escape(str(v.get('ip', '?')))}</code> "
            f"{html.escape(str(v.get('country', '')))} · {html.escape(str(v.get('ts', '')))}"
        )
    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(Command("users"))
async def cmd_users(message: types.Message):
    """Список пользователей (только для админа)."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ только для администратора.")
        return
    stat = accounts.admin_stats()
    users = accounts.list_users(limit=15)
    lines = [
        f"👥 <b>Всего: {stat['total_users']}</b> · активны сегодня: {stat['active_today']} · "
        f"VIP: {stat['vip']} · баны: {stat['banned']}\n"
    ]
    for u in users:
        name = u.get("nickname") or u.get("username") or u.get("first_name") or "Agent"
        flag = " 🚫" if u.get("banned") else ""
        role = {"admin": " 👑", "vip": " 💎"}.get(u.get("role"), "")
        lines.append(
            f"• <code>{u.get('tg_id')}</code> {html.escape(name)}{role}{flag} — "
            f"ур.{u.get('level', 1)} · {u.get('xp', 0)} XP · 📥{u.get('downloads', 0)}"
        )
    await message.answer("\n".join(lines), parse_mode="HTML")


@dp.message(Command("bc"))
async def cmd_broadcast(message: types.Message):
    """Рассылка всем пользователям: /bc текст."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ только для администратора.")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("📢 <b>Использование:</b> <code>/bc текст рассылки</code>", parse_mode="HTML")
        return
    text = parts[1]
    targets = accounts.broadcaster_targets()
    status = await message.answer(f"📢 Отправляю {len(targets)} получателям...", parse_mode="HTML")
    sent = failed = 0
    for tid in targets:
        try:
            r = await bot.send_message(tid, text)
            if r:
                sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)
    await status.edit_text(f"✅ Рассылка завершена: {sent} доставлено, {failed} ошибок (всего {len(targets)})", parse_mode="HTML")


@dp.message(Command("ban"))
async def cmd_ban(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ только для администратора.")
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("🚫 <b>Использование:</b> <code>/ban 123456789</code>", parse_mode="HTML")
        return
    res = accounts.set_banned(parts[1], True)
    if res is None:
        await message.answer("⛔ Нельзя забанить администратора.")
        return
    await message.answer(f"🚫 Пользователь <code>{parts[1]}</code> заблокирован.", parse_mode="HTML")


@dp.message(Command("unban"))
async def cmd_unban(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ только для администратора.")
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("✅ <b>Использование:</b> <code>/unban 123456789</code>", parse_mode="HTML")
        return
    accounts.set_banned(parts[1], False)
    await message.answer(f"✅ Пользователь <code>{parts[1]}</code> разблокирован.", parse_mode="HTML")



# =====================================================================
# CALLBACK QUERY BUTTONS
# =====================================================================

@dp.callback_query(F.data == "btn_quick_mail")
async def cb_quick_mail(callback: types.CallbackQuery):
    res = await TempMailService.create_inbox()
    if res.get("ok"):
        email = res.get("email")
        await callback.message.answer(f"📬 <b>Ваш временный ящик:</b>\n<code>{email}</code>", parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "btn_quick_pass")
async def cb_quick_pass(callback: types.CallbackQuery):
    pwd_res = DevSecurityTools.generate_password(18)
    await callback.message.answer(f"🔐 <b>Новый пароль:</b>\n<code>{html.escape(pwd_res['password'])}</code>", parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "btn_help_dl")
async def cb_help_dl(callback: types.CallbackQuery):
    await callback.message.answer(
        "📥 <b>Как скачивать видео:</b>\n"
        "1. Скопируйте ссылку в TikTok, Instagram (Reels), YouTube (Shorts) или Pinterest.\n"
        "2. Отправьте её в этот чат сообщением.\n"
        "3. Бот мгновенно пришлёт видео без водяных знаков!",
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data == "btn_profile")
async def cb_profile(callback: types.CallbackQuery):
    uid = callback.from_user.id
    if accounts.is_banned(uid):
        await callback.answer("⛔ Аккаунт заблокирован", show_alert=True)
        return
    if accounts.get_profile(uid) is None:
        accounts.register_user(uid, username=callback.from_user.username or "",
                               first_name=callback.from_user.first_name or "")
    p = accounts.get_profile(uid) or {}
    await callback.message.answer(_profile_text(p), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "btn_top")
async def cb_top(callback: types.CallbackQuery):
    top = accounts.leaderboard(10)
    if not top:
        await callback.answer("Пока пусто — станьте первым!", show_alert=True)
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, u in enumerate(top):
        name = u.get("nickname") or u.get("username") or u.get("first_name") or "Agent"
        medal = medals[i] if i < 3 else f"<code>{i + 1}.</code>"
        role = " 👑" if u.get("role") == "admin" else (" 💎" if u.get("role") == "vip" else "")
        lines.append(f"{medal} {html.escape(name)}{role} — ур.{u.get('level', 1)} · {u.get('xp', 0)} XP")
    await callback.message.answer("🏆 <b>Топ пользователей Multiwood:</b>\n\n" + "\n".join(lines), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "auto_dl")
async def cb_auto_dl(callback: types.CallbackQuery):
    uid = callback.from_user.id
    url = _PENDING_URLS.get(uid)
    if not url:
        await callback.answer("Ссылка устарела — отправьте её заново", show_alert=True)
        return
    await callback.answer()
    await handle_media_download(callback.message, url)


@dp.callback_query(F.data == "auto_mp3")
async def cb_auto_mp3(callback: types.CallbackQuery):
    uid = callback.from_user.id
    url = _PENDING_URLS.pop(uid, None)
    if not url:
        await callback.answer("Ссылка устарела — отправьте её заново", show_alert=True)
        return
    await callback.answer()
    await handle_media_download(callback.message, url, extract_audio=True)



# =====================================================================
# ACCOUNT COMMANDS (/profile, /nick, /daily, /top)
# =====================================================================

def _profile_text(p: dict) -> str:
    name = html.escape(p.get("nickname") or p.get("first_name") or "Agent")
    uname = f"@{p.get('username')}" if p.get("username") else "—"
    role_ru = {"admin": "👑 Администратор", "vip": "💎 VIP", "user": "👤 Пользователь"}
    xp = int(p.get("xp", 0))
    level = int(p.get("level", 1))
    need = accounts.xp_for_next_level(level)
    progress = min(100, max(0, xp * 100 // need)) if need else 0
    bars = "█" * (progress // 10) + "░" * (10 - progress // 10)
    return (
        f"👤 <b>Профиль: {name}</b>\n"
        f"🆔 ID: <code>{p.get('tg_id')}</code>\n"
        f"📛 Ник: <code>{html.escape(p.get('nickname') or 'не задан')}</code> (/nick имя)\n"
        f"ℹ️ Telegram: {uname}\n"
        f"🏅 Роль: {role_ru.get(p.get('role'), p.get('role'))}\n"
        f"📈 Уровень {level} · XP {xp}/{need} [{bars}]\n"
        f"🔥 Серия дней: {p.get('daily_streak', 0)}\n"
        f"📥 Скачано: {p.get('downloads', 0)} · 📬 Почт: {p.get('mails', 0)} · 🔍 Сканов: {p.get('scans', 0)}\n"
        f"🗓 С нами с: {str(p.get('created_at', ''))[:10]}"
    )


@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    if register_or_update(message):
        await message.answer("⛔ Ваш аккаунт заблокирован администратором.")
        return
    p = accounts.get_profile(message.from_user.id) or {}
    await message.answer(_profile_text(p), parse_mode="HTML")


@dp.message(Command("nick"))
async def cmd_nick(message: types.Message):
    if register_or_update(message):
        await message.answer("⛔ Ваш аккаунт заблокирован администратором.")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or len(parts[1].strip()) > 24:
        await message.answer("📛 <b>Использование:</b> <code>/nick ИмяДо24Символов</code>", parse_mode="HTML")
        return
    accounts.update_profile(message.from_user.id, nickname=parts[1].strip())
    await message.answer(f"✅ Ник обновлён: <b>{html.escape(parts[1].strip())}</b>", parse_mode="HTML")


@dp.message(Command("daily"))
async def cmd_daily(message: types.Message):
    if register_or_update(message):
        await message.answer("⛔ Ваш аккаунт заблокирован администратором.")
        return
    res = accounts.claim_daily(message.from_user.id)
    if not res.get("ok"):
        await message.answer("❌ Ошибка получения бонуса.")
        return
    if res.get("already"):
        await message.answer(
            f"🎁 Бонус уже получен сегодня! 🔥 Серия: <b>{res['streak']}</b> дн.",
            parse_mode="HTML",
        )
        return
    await message.answer(
        f"🎁 <b>Ежедневный бонус получен: +{res['xp_gained']} XP!</b>\n"
        f"🔥 Серия подряд: <b>{res['streak']}</b> дн.\n"
        f"Возвращайтесь завтра, чтобы серия не прервалась.",
        parse_mode="HTML",
    )


@dp.message(Command("top"))
async def cmd_top(message: types.Message):
    top = accounts.leaderboard(10)
    if not top:
        await message.answer("🏆 Пока пусто — станьте первым! Используйте бота и получайте XP.")
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, u in enumerate(top):
        name = u.get("nickname") or u.get("username") or u.get("first_name") or "Agent"
        medal = medals[i] if i < 3 else f"<code>{i + 1}.</code>"
        role = " 👑" if u.get("role") == "admin" else (" 💎" if u.get("role") == "vip" else "")
        lines.append(f"{medal} {html.escape(name)}{role} — ур.{u.get('level', 1)} · {u.get('xp', 0)} XP")
    await message.answer("🏆 <b>Топ пользователей Multiwood:</b>\n\n" + "\n".join(lines), parse_mode="HTML")


# =====================================================================
# OSINT COMMANDS (учебные, только публичные данные)
# =====================================================================

def _format_osint_result(res: dict) -> str:
    """Компактное форматирование результатов разных модулей."""
    t = html.escape(str(res.get("target", "")))

    if "found_count" in res:
        lines = [f"🔍 <b>Никнейм {t}</b>: найдено <b>{res['found_count']}</b> из {res.get('checked_sites', '?')} сайтов"]
        for p in (res.get("profiles") or [])[:15]:
            lines.append(f"• <a href='{html.escape(p['url'])}'>{html.escape(p['site'])}</a>")
        if res.get("found_count", 0) > 15:
            lines.append(f"… и ещё {res['found_count'] - 15}")
        if res.get("found_count", 0) == 0:
            lines.append("Аккаунты не найдены — возможно, ник уникален.")
        return "\n".join(lines)

    if "carrier" in res:
        return (
            f"☎️ <b>Номер {t}</b>\n"
            f"🌍 Страна: {html.escape(str(res.get('country', 'N/A')))} ({res.get('country_code', '')})\n"
            f"📡 Оператор: {html.escape(str(res.get('carrier', 'N/A')))}\n"
            f"📍 Регион: {html.escape(str(res.get('location', 'N/A')))}\n"
            f"📱 Тип: {res.get('line_type', 'N/A')}\n"
            f"📞 Формат: <code>{html.escape(str(res.get('formatted_international', '')))}</code>\n"
            f"<i>{html.escape(str(res.get('warning', '')))}</i>"
        )

    if "root_handle" in res:
        sigs = "".join(f"\n• {html.escape(s)}" for s in res.get("signals", [])) or "\n• Особых признаков нет"
        return (
            f"🕵️ <b>Атрибуция {t}</b>\n"
            f"Корневой хэндл: <code>{html.escape(res['root_handle'])}</code>\n"
            f"Это вариант: {'да' if res.get('is_variant') else 'нет'}\n"
            f"Уверенность: {res.get('confidence', 0)}%{sigs}\n"
            f"<i>{html.escape(str(res.get('warning', '')))}</i>"
        )

    data = res.get("data") or {}

    if "ip_addresses" in data:
        ips = ", ".join(f"<code>{html.escape(i)}</code>" for i in data.get("ip_addresses", [])[:6]) or "не разрешается"
        http = data.get("http", {})
        return (
            f"🌐 <b>Домен {t}</b>\n"
            f"IP: {ips}\n"
            f"HTTP: {http.get('status_code', 'N/A')} · сервер: {html.escape(str(http.get('server', 'N/A')))}\n"
            f"HTTPS: {'да' if http.get('https') else 'нет'} · HSTS: {'да' if http.get('hsts') else 'нет'}"
        )

    if "country" in data or "city" in data:
        return (
            f"🌍 <b>IP {t}</b>\n"
            f"Страна: {html.escape(str(data.get('country', 'N/A')))} ({data.get('country_code', '')})\n"
            f"Город: {html.escape(str(data.get('city', 'N/A')))} · {html.escape(str(data.get('region', '')))}\n"
            f"Провайдер: {html.escape(str(data.get('org', 'N/A')))} (ASN {data.get('asn', '')})\n"
            f"Координаты: {data.get('latitude', '?')}, {data.get('longitude', '?')}"
        )

    if "mx_records" in data:
        mx = ", ".join(f"<code>{html.escape(m)}</code>" for m in data.get("mx_records", [])[:5]) or "не найдены"
        return (
            f"✉️ <b>Email {t}</b>\n"
            f"Домен: {html.escape(str(data.get('domain', '')))}\n"
            f"MX: {mx}\n"
            f"Бесплатный провайдер: {'да' if data.get('is_free_provider') else 'нет'}"
        )

    if "dorks" in res:
        lines = [f"🔎 <b>Google-dorks для {t}:</b>"]
        for d in res["dorks"][:8]:
            lines.append(f"• {html.escape(d['title'])}:\n<code>{html.escape(d['query'])}</code>")
        return "\n".join(lines)

    if "exists" in data:
        if not data.get("exists"):
            return f"🔍 <b>{t}</b>: аккаунт не найден."
        return (
            f"🔍 <b>{t}</b>: найден\n"
            f"Имя: {html.escape(str(data.get('name') or '—'))}\n"
            f"Описание: {html.escape(str(data.get('bio') or data.get('description') or '—'))[:200]}\n"
            f"Репозиториев: {data.get('public_repos', '—')} · Подписчиков: {data.get('followers', '—')}\n"
            f"Профиль: {html.escape(str(data.get('profile') or data.get('url') or ''))}"
        )

    if "snapshots_found" in res:
        return (
            f"🕰 <b>Wayback {t}</b>: снимков найдено {res['snapshots_found']}\n"
            f"Архив: {html.escape(str(data.get('archive_url', '')))}"
        )

    return f"✅ <b>{t}</b>: " + html.escape(json.dumps(res, ensure_ascii=False)[:800])


async def _osint_reply(message: types.Message, coro, title: str):
    """Общая обёртка OSINT-команд: бан-гард → индикатор → результат + XP."""
    if register_or_update(message):
        await message.answer("⛔ Ваш аккаунт заблокирован администратором.")
        return
    status = await message.answer(f"🔍 <i>{title}...</i>", parse_mode="HTML")
    try:
        res = await coro
    except Exception as e:
        await status.edit_text(f"❌ Сбой модуля: {html.escape(str(e)[:150])}", parse_mode="HTML")
        return
    if not res.get("ok"):
        await status.edit_text(f"❌ {html.escape(res.get('error', 'Ошибка'))}", parse_mode="HTML")
        return
    accounts.bump_counter(message.from_user.id, "scans")
    accounts.add_xp(message.from_user.id, accounts.XP_SCAN)
    await status.edit_text(_format_osint_result(res), parse_mode="HTML")


@dp.message(Command("username"))
async def cmd_username_scan(message: types.Message):
    from osint import UsernameScanner
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("🔍 <b>Использование:</b> <code>/username ник</code>", parse_mode="HTML")
        return
    await _osint_reply(message, UsernameScanner.scan(parts[1]), "Ищу никнейм по сайтам")


@dp.message(Command("phone"))
async def cmd_phone_scan(message: types.Message):
    from osint import PhoneRecon
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("☎️ <b>Использование:</b> <code>/phone +79991234567</code>", parse_mode="HTML")
        return
    await _osint_reply(message, asyncio.to_thread(PhoneRecon.analyze, parts[1]), "Анализирую номер")


@dp.message(Command("ip"))
async def cmd_ip_scan(message: types.Message):
    from osint import IpGeoint
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("🌍 <b>Использование:</b> <code>/ip 1.1.1.1</code>", parse_mode="HTML")
        return
    await _osint_reply(message, IpGeoint.analyze(parts[1]), "Определяю геолокацию IP")


@dp.message(Command("domain"))
async def cmd_domain_scan(message: types.Message):
    from osint import DomainRecon
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("🌐 <b>Использование:</b> <code>/domain site.com</code>", parse_mode="HTML")
        return
    await _osint_reply(message, DomainRecon.analyze(parts[1]), "Делаю DNS-разведку домена")


@dp.message(Command("dorks"))
async def cmd_dorks(message: types.Message):
    from osint import GoogleDorks
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("🔎 <b>Использование:</b> <code>/dorks компания или домен</code>", parse_mode="HTML")
        return
    await _osint_reply(message, GoogleDorks.generate(parts[1]), "Генерирую поисковые запросы")


# =====================================================================
# OMNI-LINK DISPATCHER (AUTO-DOWNLOAD FOR SOCIAL LINKS)
# =====================================================================


@dp.message(F.text)
async def handle_text_messages(message: types.Message):
    text = (message.text or "").strip()

    # Игнорируем команды
    if text.startswith("/"):
        await message.answer("❓ Неизвестная команда. Введите <code>/help</code> для списка команд.", parse_mode="HTML")
        return

    # Бан-гард для любых текстовых сообщений
    if message.from_user and accounts.is_banned(message.from_user.id):
        await message.answer("⛔ Ваш аккаунт заблокирован администратором.")
        return

    # Автоматическое скачивание при отправке медиа-ссылки
    if MediaDownloader.is_media_url(text):
        await handle_media_download(message, text)
        return

    # Если обычная ссылка — запоминаем URL в памяти (callback_data лимит 64 байта!)
    if text.startswith("http://") or text.startswith("https://"):
        uid = message.from_user.id if message.from_user else 0
        if len(text) > 4000:
            await message.answer("❌ Слишком длинная ссылка.")
            return
        _PENDING_URLS[uid] = text
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📥 Скачать видео", callback_data="auto_dl"),
                    InlineKeyboardButton(text="🎵 Извлечь MP3", callback_data="auto_mp3")
                ]
            ]
        )
        await message.answer(
            f"🔗 <b>Обнаружена ссылка:</b>\n<code>{html.escape(text[:300])}</code>\n\nВыберите действие:",
            reply_markup=kb,
            parse_mode="HTML"
        )
        return


    # Ответ на обычный текст
    await message.answer(
        "👋 Отправьте ссылку на видео из <b>TikTok, Reels, Shorts</b> для мгновенного скачивания, "
        "или откройте <b>Мультитул</b> кнопкой ниже!",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )


# =====================================================================
# STARTUP & MAIN
# =====================================================================

async def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting Multiwood Telegram Bot...")

    try:
        if DOMAIN:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="⚡ Мультитул",
                    web_app=WebAppInfo(url=get_webapp_url())
                )
            )
        await bot.set_my_commands([
            BotCommand(command="start", description="📱 Открыть Мультитул"),
            BotCommand(command="dl", description="📥 Скачать видео/аудио из соцсетей"),
            BotCommand(command="profile", description="👤 Мой профиль и статистика"),
            BotCommand(command="daily", description="🎁 Ежедневный бонус XP"),
            BotCommand(command="top", description="🏆 Топ пользователей"),
            BotCommand(command="username", description="🔍 Поиск никнейма по сайтам"),
            BotCommand(command="phone", description="☎️ Инфо о телефонном номере"),
            BotCommand(command="ip", description="🌍 Геолокация IP-адреса"),
            BotCommand(command="domain", description="🌐 DNS-разведка домена"),
            BotCommand(command="mail", description="📬 Одноразовая временная почта"),
            BotCommand(command="pass", description="🔐 Генератор стойких паролей"),
            BotCommand(command="qr", description="📷 Создать QR-код"),
            BotCommand(command="clean", description="🪄 Убрать трекеры из ссылки"),
            BotCommand(command="hash", description="🔐 Хэши текста (MD5/SHA)"),
            BotCommand(command="sum", description="🧠 AI-выжимка статьи"),
            BotCommand(command="help", description="ℹ️ Список всех команд"),
        ])
    except Exception as e:
        logging.warning(f"Menu button config notice: {e}")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
