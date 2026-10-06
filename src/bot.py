"""
Multiwood Telegram Bot - Smart Mobile Multitool
Fast social media downloader, mobile utilities, and Telegram Mini App integration.
"""

import asyncio
import html
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


def is_admin(user_id: int) -> bool:
    return bool(ADMIN_CHAT_ID) and str(user_id) == str(ADMIN_CHAT_ID)


def get_webapp_url() -> str:
    sep = "&" if "?" in DOMAIN else "?"
    return f"{DOMAIN}{sep}v=3.0"


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
                InlineKeyboardButton(text="ℹ️ Как скачать видео", callback_data="btn_help_dl")
            ]
        ]
    )


# =====================================================================
# BASIC COMMANDS
# =====================================================================

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_name = message.from_user.first_name or "друг"
    admin_hint = "\n\n👑 <b>Админ-панель:</b> <code>/admin</code>" if is_admin(message.from_user.id) else ""

    text = (
        f"👋 <b>Привет, {html.escape(user_name)}!</b>\n"
        f"Добро пожаловать в <b>Multiwood</b> — твой персональный мультитул для смартфона.\n\n"
        f"📥 <b>СКАЧИВАНИЕ ИЗ СОЦСЕТЕЙ БЕЗ ВОДЯНЫХ ЗНАКОВ:</b>\n"
        f"Просто <b>отправь ссылку</b> в чат (TikTok, Instagram Reels, YouTube Shorts, X, Pinterest, VK) — и бот пришлёт чистое видео или аудио!\n\n"
        f"🛠 <b>МОБИЛЬНЫЕ УТИЛИТЫ:</b>\n"
        f"Временная почта, генератор паролей, QR-коды, очистка ссылок от трекеров и AI-выжимка.\n\n"
        f"⚡ <i>Нажми кнопку ниже, чтобы открыть полноэкранный Mini App:</i>"
        f"{admin_hint}"
    )
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="HTML")


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "📖 <b>Инструкция по использованию Multiwood:</b>\n\n"
        "1️⃣ <b>Скачать видео:</b> просто пришли ссылку сообщением в этот чат или используй <code>/dl ссылка</code>.\n"
        "2️⃣ <b>Временная почта:</b> команда <code>/mail</code> создаст одноразовый ящик для кодов и регистраций.\n"
        "3️⃣ <b>Генератор паролей:</b> команда <code>/pass</code> сгенерирует сверхстойкий пароль.\n"
        "4️⃣ <b>QR-код:</b> <code>/qr ваш_текст</code> — моментально создаст QR-изображение.\n"
        "5️⃣ <b>Mini App:</b> нажми кнопку меню слева от поля ввода для графического интерфейса!"
    )
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="HTML")


# =====================================================================
# MEDIA DOWNLOADER (SMART LINK SNIFFER)
# =====================================================================

async def handle_media_download(message: types.Message, url: str, extract_audio: bool = False):
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

    # Автоматическое скачивание при отправке медиа-ссылки
    if MediaDownloader.is_media_url(text):
        await handle_media_download(message, text)
        return

    # Если обычная ссылка
    if text.startswith("http://") or text.startswith("https://"):
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📥 Скачать видео", callback_data=f"auto_dl:{text[:120]}"),
                    InlineKeyboardButton(text="🎵 Извлечь MP3", callback_data=f"auto_mp3:{text[:120]}")
                ]
            ]
        )
        await message.answer(
            f"🔗 <b>Обнаружена ссылка:</b>\n<code>{html.escape(text)}</code>\n\nВыберите действие:",
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
            BotCommand(command="mail", description="📬 Одноразовая временная почта"),
            BotCommand(command="pass", description="🔐 Генератор стойких паролей"),
            BotCommand(command="qr", description="📷 Создать QR-код"),
            BotCommand(command="help", description="ℹ️ Инструкция и помощь"),
        ])
    except Exception as e:
        logging.warning(f"Menu button config notice: {e}")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
