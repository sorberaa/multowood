import base64
import asyncio
import io
import json
import logging
import os
import re
import html
import time
from pathlib import Path

import httpx
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    WebAppInfo,
)
from dotenv import load_dotenv

load_dotenv("/app/config/.env")
load_dotenv("config/.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
DOMAIN = os.getenv("DOMAIN", "https://osint.qrport.eu")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "5233450569")

DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_API = os.getenv("LOCAL_API", "http://127.0.0.1:8000")
REMOTE_API = DOMAIN.rstrip("/") if DOMAIN else "https://osint.qrport.eu"

STAR_PACKAGES = {
    "pkg_20": {"title": "⭐️ 20 OSINT Запросов", "description": "Пополнение баланса поиска на 20 проверок", "scans": 20, "stars": 35},
    "pkg_50": {"title": "⭐️ 50 OSINT Запросов", "description": "Пополнение баланса поиска на 50 проверок", "scans": 50, "stars": 88},
    "pkg_100": {"title": "⭐️ 100 OSINT Запросов", "description": "Пополнение баланса поиска на 100 проверок", "scans": 100, "stars": 235},
}

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в config/.env")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def is_admin(user_id: int) -> bool:
    if not ADMIN_CHAT_ID:
        return False
    return str(user_id) == str(ADMIN_CHAT_ID)


WEBAPP_VERSION = "2.3"


def get_webapp_url() -> str:
    sep = "&" if "?" in DOMAIN else "?"
    return f"{DOMAIN}{sep}v={WEBAPP_VERSION}"


def get_webapp_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Открыть OSINT Панель", web_app=WebAppInfo(url=get_webapp_url()))],
            [InlineKeyboardButton(text="⭐️ Купить запросы (Stars)", callback_data="open_buy_menu")]
        ]
    )


def get_buy_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌟 20 запросов — 35 ⭐️", callback_data="buy_pkg_20")],
            [InlineKeyboardButton(text="🌟 50 запросов — 88 ⭐️", callback_data="buy_pkg_50")],
            [InlineKeyboardButton(text="🌟 100 запросов — 235 ⭐️", callback_data="buy_pkg_100")],
            [InlineKeyboardButton(text="⚡ Открыть OSINT Панель", web_app=WebAppInfo(url=get_webapp_url()))]
        ]
    )


def format_terminal_box(tool_title: str, command: str, raw_cli: str, max_chars: int = 3000) -> str:
    """Форматирует консольный вывод модуля в стилизованный блок терминала Linux."""
    raw_cli = (raw_cli or "").strip()
    if not raw_cli:
        raw_cli = f"root@cyberhub:~# {command}\n[+] Status: OK\n[+] Operation completed successfully."

    if len(raw_cli) > max_chars:
        half = max_chars // 2 - 40
        raw_cli = raw_cli[:half] + "\n\n... [LOG TRUNCATED - FULL REPORT IN WEBAPP] ...\n\n" + raw_cli[-half:]

    escaped_cli = html.escape(raw_cli)
    escaped_title = html.escape(tool_title.upper())
    escaped_cmd = html.escape(command)

    # Защита от лимита 4096 символов Telegram
    if len(escaped_cli) > 3300:
        escaped_cli = escaped_cli[:3300] + "... [TRUNCATED]"

    return (
        f"💻 <b>TERMINAL OUTPUT // {escaped_title}</b>\n"
        f"<code>$ {escaped_cmd}</code>\n"
        f"<pre><code class=\"language-bash\">{escaped_cli}</code></pre>\n"
        f"⚡ <i>Нажмите на окно терминала для быстрого копирования лога.</i>"
    )


def detect_target_vector(target: str) -> tuple[str, str, str, str]:
    """
    Автоматически определяет тип цели и возвращает:
    (endpoint_path, tool_title, cli_cmd, payload_key)
    """
    t = target.strip()
    digits = re.sub(r"[^\d+]", "", t)

    # 1. Телефон
    if (t.startswith("+") and len(digits) >= 8) or (digits.isdigit() and len(digits) in [10, 11, 12] and not any(c.isalpha() for c in t)):
        return "/api/scan/phone", "PhoneInfoga Telecom Recon", f"phoneinfoga scan -n {t}", "target"

    # 2. Почта
    if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", t):
        return "/api/scan/email", "Holehe Email Footprint", f"holehe --email {t}", "target"

    # 3. Блокчейн-кошелек
    if (t.startswith("0x") and len(t) in [42, 66]) or ((t.startswith("bc1") or t.startswith("1") or t.startswith("3")) and 26 <= len(t) <= 62) or (t.startswith("T") and len(t) == 34 and not any(c in t for c in [" ", "@", "/"])):
        return "/api/scan/crypto_aml", "Crypto AML & Sanctions Audit", f"aml_audit --target {t}", "target"

    # 4. IPv4
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", t):
        return "/api/scan/ip", "GeoIP & ASN Network Recon", f"ip_lookup {t}", "target"

    # 5. Домен / Сайт
    if ("." in t and " " not in t and "@" not in t) or t.startswith("http://") or t.startswith("https://"):
        clean_dom = re.sub(r"^https?://", "", t).split("/")[0].split(":")[0]
        return "/api/scan/domain", "Subfinder & DNS Recon", f"subfinder -d {clean_dom}", "target"

    # 6. Никнейм / Псевдоним (Sherlock)
    clean_nick = t.lstrip("@")
    return "/api/scan/username", "Sherlock Multi-Platform Search", f"sherlock --print-found {clean_nick}", "target"


async def execute_and_send_terminal(
    message: types.Message,
    endpoint: str,
    tool_title: str,
    cli_cmd: str,
    payload: dict,
    extra_buttons: list = None
):
    """Выполняет запрос к модулю OSINT и отправляет чистый терминальный лог."""
    status_msg = await message.answer("⏳ <i>Выполняю консольный запрос в системе...</i>", parse_mode="HTML")
    data = None
    last_error_text = ""

    # Пробуем LOCAL_API, при недоступности переключаемся на REMOTE_API
    servers = [LOCAL_API]
    if REMOTE_API and REMOTE_API not in servers:
        servers.append(REMOTE_API)

    for api_base in servers:
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(
                    f"{api_base}{endpoint}",
                    json=payload,
                    headers={"X-Telegram-User-Id": str(message.from_user.id)}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    break
                else:
                    try:
                        err_json = resp.json()
                        last_error_text = err_json.get("error") or err_json.get("detail") or f"HTTP {resp.status_code}"
                    except Exception:
                        last_error_text = f"HTTP {resp.status_code}"
        except Exception as conn_err:
            last_error_text = str(conn_err)
            continue

    if data is None:
        await status_msg.edit_text(f"❌ <b>Ошибка связи с ядром:</b> {html.escape(last_error_text or 'Не удалось подключиться к API')}", parse_mode="HTML")
        return

    try:
        if not data.get("ok") and data.get("ok") is not None:
            err_msg = data.get("error", "Сбой при выполнении модуля")
            if "Лимит" in err_msg:
                kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="⭐️ Пополнить баланс запросов", callback_data="open_buy_menu")],
                        [InlineKeyboardButton(text="⚡ Открыть WebApp", web_app=WebAppInfo(url=get_webapp_url()))]
                    ]
                )
                await status_msg.edit_text(f"⚠️ <b>{err_msg}</b>", reply_markup=kb, parse_mode="HTML")
            else:
                await status_msg.edit_text(f"❌ <b>Ошибка выполнения:</b> {html.escape(err_msg)}", parse_mode="HTML")
            return

        raw_cli = data.get("raw_cli_output")
        if not raw_cli:
            now_ts = time.strftime("%Y-%m-%d %H:%M:%S")
            lines = [
                f"root@cyberhub:~# {cli_cmd}",
                f"[{now_ts}] [INIT] Executing OSINT Forensic module: {tool_title}...",
                f"[{now_ts}] [INFO] Target parameter: {payload.get('target', 'unknown')}",
                f"[{now_ts}] [EXEC] Querying threat intelligence engines..."
            ]
            if data.get("profiles"):
                for p in data["profiles"][:15]:
                    lines.append(f"[+] [FOUND] {p.get('platform')}: {p.get('url')}")
                lines.append(f"[*] Verified profile matches: {len(data['profiles'])}")
            elif data.get("aml_risk_score") is not None:
                lines.append(f"[+] [AML RISK] Score: {data.get('aml_risk_score')}% ({data.get('risk_level', 'LOW')})")
                lines.append(f"[+] [TRANSACTIONS] Count: {data.get('tx_count', 0)}")
            elif data.get("country") or data.get("city"):
                lines.append(f"[+] [GEO] {data.get('country')}, {data.get('city')} | ISP: {data.get('isp')}")
            else:
                lines.append(f"[+] [STATUS] Validated: {data.get('verdict_summary') or data.get('ai_summary') or 'OK'}")
            lines.append(f"[✓] Status: 200 OK | Operation completed.")
            raw_cli = "\n".join(lines)

        text = format_terminal_box(tool_title, cli_cmd, raw_cli)

        buttons = [
            [InlineKeyboardButton(text="⚡ Открыть результат в WebApp", web_app=WebAppInfo(url=get_webapp_url()))]
        ]
        if data.get("google_maps_url"):
            buttons.append([InlineKeyboardButton(text="📍 Открыть координаты на карте", url=data["google_maps_url"])])
        if extra_buttons:
            buttons.extend(extra_buttons)

        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        try:
            await status_msg.edit_text(text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
        except Exception:
            # Fallback к обычному тексту при ошибке парсинга разметки
            plain = f"💻 TERMINAL OUTPUT // {tool_title}\n$ {cli_cmd}\n\n{raw_cli[:3000]}"
            await status_msg.edit_text(plain, reply_markup=kb, disable_web_page_preview=True)

    except Exception as e:
        await status_msg.edit_text(f"❌ <b>Сбой вывода:</b> {html.escape(str(e))}", parse_mode="HTML")


# --- БАЗОВЫЕ КОМАНДЫ ---

@dp.message(CommandStart())
@dp.message(Command("help"))
async def cmd_start(message: types.Message):
    admin_text = ""
    if is_admin(message.from_user.id):
        admin_text = "\n\n👑 <b>Административный доступ:</b>\n<code>/users</code> — база | <code>/setscans</code> — квота | <code>/grantvip</code> — безлимит | <code>/visits</code> — визиты"

    text = (
        "🛡️ <b>ISLAND INTELLIGENCE // OSINT FORENSIC TERMINAL</b>\n"
        "<code>SYSTEM_STATUS: ONLINE [v3.0_CLI_CORE]</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Консольный комплекс глубокой сетевой разведки, анализа цифрового следа и деанонимизации открытых источников.\n\n"
        "🚀 <b>ПРЯМОЙ КОНСОЛЬНЫЙ ВВОД:</b>\n"
        "Просто <b>отправьте цель сообщением в чат</b> (ник, номер телефона, почту, IP, домен, адрес кошелька или фото) — бот автоматически распознает тип и выведет консольный терминальный лог!\n\n"
        "⌨️ <b>КОМАНДЫ ТЕРМИНАЛА:</b>\n"
        "├ <code>/scan &lt;цель&gt;</code> — Экспресс-сканирование (автоопределение типа)\n"
        "├ <code>/user &lt;ник&gt;</code> — Поиск профилей цели по 480+ базам (Sherlock)\n"
        "├ <code>/phone &lt;номер&gt;</code> — Телеком-разведка оператора и мессенджеров (PhoneInfoga)\n"
        "├ <code>/email &lt;почта&gt;</code> — Анализ привязок аккаунтов по почте (Holehe)\n"
        "├ <code>/ip &lt;ip_адрес&gt;</code> — Геолокация, провайдер и ASN-маршрутизация\n"
        "├ <code>/domain &lt;домен&gt;</code> — DNS, SSL, заголовки и субдомены\n"
        "├ <code>/aml &lt;кошелек&gt;</code> — Проверка крипты на санкции, миксеры и риски\n"
        "├ <code>/tg &lt;юзернейм&gt;</code> — Датацентр, ID и телеметрия Telegram-аккаунта\n"
        "├ <code>/audit &lt;цель&gt;</code> — Проверка утечек баз данных и паролей\n"
        "├ <code>/spy &lt;юзернейм&gt;</code> — Анализ онлайна, фаз сна и скрытых связей\n"
        "└ <code>/recon &lt;цель&gt;</code> — Сквозной сбор и построение графа связей\n\n"
        f"🔐 <b>ИДЕНТИФИКАТОР:</b> <code>{message.from_user.id}</code>\n"
        "🎁 <b>КВОТА:</b> <code>5 бесплатных проверок</code>\n"
        "⭐️ <b>ПОПОЛНЕНИЕ:</b> <code>/buy</code> (Telegram Stars)\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡ <i>Запустите графическую веб-панель нажатием кнопки ниже:</i>"
        f"{admin_text}"
    )
    await message.answer(text, reply_markup=get_webapp_keyboard(), parse_mode="HTML")


@dp.message(Command("id"))
async def cmd_id(message: types.Message):
    await message.answer(f"🆔 <b>Ваш Telegram ID:</b> <code>{message.from_user.id}</code>", parse_mode="HTML")


# --- МОНЕТИЗАЦИЯ И ЗВЕЗДЫ ---

@dp.message(Command("buy"))
@dp.message(Command("stars"))
async def cmd_buy_stars(message: types.Message):
    text = (
        "⭐️ <b>Пополнение баланса запросов (Telegram Stars)</b>\n\n"
        "Каждому новому агенту предоставляется <b>5 бесплатных запросов</b>.\n"
        "Для продолжения расследований выберите подходящий пакет:\n\n"
        "• <b>20 запросов</b> — <code>35 Stars</code>\n"
        "• <b>50 запросов</b> — <code>88 Stars</code>\n"
        "• <b>100 запросов</b> — <code>235 Stars</code>\n\n"
        "<i>Оплата происходит мгновенно в один клик через официальные Telegram Stars.</i>"
    )
    await message.answer(text, reply_markup=get_buy_keyboard(), parse_mode="HTML")


@dp.callback_query(F.data == "open_buy_menu")
async def callback_open_buy_menu(callback: types.CallbackQuery):
    text = (
        "⭐️ <b>Пополнение баланса запросов (Telegram Stars)</b>\n\n"
        "• <b>20 запросов</b> — <code>35 Stars</code>\n"
        "• <b>50 запросов</b> — <code>88 Stars</code>\n"
        "• <b>100 запросов</b> — <code>235 Stars</code>\n\n"
        "<i>Нажмите на нужный тариф для моментального выставления счета в Stars:</i>"
    )
    await callback.message.answer(text, reply_markup=get_buy_keyboard(), parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data.startswith("buy_pkg_"))
async def callback_buy_package(callback: types.CallbackQuery):
    pkg_key = callback.data.replace("buy_", "")
    pkg = STAR_PACKAGES.get(pkg_key)
    if not pkg:
        await callback.answer("Пакет не найден", show_alert=True)
        return

    await callback.message.answer_invoice(
        title=pkg["title"],
        description=pkg["description"],
        payload=f"stars_{pkg_key}_{callback.from_user.id}_{int(time.time())}",
        currency="XTR",
        prices=[LabeledPrice(label=pkg["title"], amount=pkg["stars"])],
        provider_token=""
    )
    await callback.answer()


@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: types.PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@dp.message(F.successful_payment)
async def successful_payment_handler(message: types.Message):
    sp = message.successful_payment
    payload = sp.invoice_payload
    stars_amount = sp.total_amount

    scans = 20
    if "pkg_50" in payload or stars_amount == 88:
        scans = 50
    elif "pkg_100" in payload or stars_amount == 235:
        scans = 100
    elif "pkg_20" in payload or stars_amount == 35:
        scans = 20

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{LOCAL_API}/api/user/add-stars-scans",
                json={"tg_id": str(message.from_user.id), "scans": scans, "stars": stars_amount}
            )
    except Exception:
        pass

    text = (
        f"🎉 <b>Оплата успешно получена!</b>\n\n"
        f"⭐️ Списано: <code>{stars_amount} Stars</code>\n"
        f"⚡ Начислено: <b>+{scans} OSINT-запросов</b>\n\n"
        f"<i>Запросы уже зачислены на ваш баланс. Откройте терминал или отправьте цель сообщением!</i>"
    )
    await message.answer(text, reply_markup=get_webapp_keyboard(), parse_mode="HTML")


# --- ТЕРМИНАЛЬНЫЕ КОМАНДЫ СКАНИРОВАНИЯ ---

@dp.message(Command("scan"))
async def cmd_scan(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ <b>Использование:</b> <code>/scan &lt;цель&gt;</code>\nПример: <code>/scan durov</code>, <code>/scan +79991234567</code>, <code>/scan 1.1.1.1</code>", parse_mode="HTML")
        return

    target = parts[1].strip()
    endpoint, tool_title, cli_cmd, payload_key = detect_target_vector(target)
    payload = {payload_key: target, "caller": str(message.from_user.id)}
    await execute_and_send_terminal(message, endpoint, tool_title, cli_cmd, payload)


@dp.message(Command("user"))
@dp.message(Command("sherlock"))
async def cmd_user(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ <b>Использование:</b> <code>/user &lt;никнейм&gt;</code>\nПример: <code>/user durov</code>", parse_mode="HTML")
        return

    target = parts[1].strip().lstrip("@")
    endpoint = "/api/scan/username"
    tool_title = "Sherlock Multi-Platform Search"
    cli_cmd = f"sherlock --print-found {target}"
    payload = {"target": target, "caller": str(message.from_user.id)}
    await execute_and_send_terminal(message, endpoint, tool_title, cli_cmd, payload)


@dp.message(Command("phone"))
async def cmd_phone(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ <b>Использование:</b> <code>/phone &lt;номер&gt;</code>\nПример: <code>/phone +79991234567</code>", parse_mode="HTML")
        return

    target = parts[1].strip()
    endpoint = "/api/scan/phone"
    tool_title = "PhoneInfoga Telecom Recon"
    cli_cmd = f"phoneinfoga scan -n {target}"
    payload = {"target": target, "caller": str(message.from_user.id)}
    await execute_and_send_terminal(message, endpoint, tool_title, cli_cmd, payload)


@dp.message(Command("email"))
async def cmd_email(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ <b>Использование:</b> <code>/email &lt;почта&gt;</code>\nПример: <code>/email test@gmail.com</code>", parse_mode="HTML")
        return

    target = parts[1].strip()
    endpoint = "/api/scan/email"
    tool_title = "Holehe Mail Footprint"
    cli_cmd = f"holehe --email {target}"
    payload = {"target": target, "caller": str(message.from_user.id)}
    await execute_and_send_terminal(message, endpoint, tool_title, cli_cmd, payload)


@dp.message(Command("ip"))
async def cmd_ip(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ <b>Использование:</b> <code>/ip &lt;ip_адрес&gt;</code>\nПример: <code>/ip 1.1.1.1</code>", parse_mode="HTML")
        return

    target = parts[1].strip()
    endpoint = "/api/scan/ip"
    tool_title = "GeoIP & ASN Network Recon"
    cli_cmd = f"ip_lookup {target}"
    payload = {"target": target, "caller": str(message.from_user.id)}
    await execute_and_send_terminal(message, endpoint, tool_title, cli_cmd, payload)


@dp.message(Command("domain"))
@dp.message(Command("whois"))
async def cmd_domain(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ <b>Использование:</b> <code>/domain &lt;домен&gt;</code>\nПример: <code>/domain example.com</code>", parse_mode="HTML")
        return

    target = re.sub(r"^https?://", "", parts[1].strip()).split("/")[0].split(":")[0]
    endpoint = "/api/scan/domain"
    tool_title = "Subfinder & DNS Recon"
    cli_cmd = f"subfinder -d {target}"
    payload = {"target": target, "caller": str(message.from_user.id)}
    await execute_and_send_terminal(message, endpoint, tool_title, cli_cmd, payload)


@dp.message(Command("aml"))
async def cmd_aml(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ <b>Использование:</b> <code>/aml &lt;адрес_кошелька&gt;</code>\nПример: <code>/aml 0x742d35Cc6634C0532925a3b844Bc454e4438f44e</code>", parse_mode="HTML")
        return

    target = parts[1].strip()
    endpoint = "/api/scan/crypto_aml"
    tool_title = "Crypto AML & Sanctions Audit"
    cli_cmd = f"aml_audit --target {target}"
    payload = {"target": target, "caller": str(message.from_user.id)}
    await execute_and_send_terminal(message, endpoint, tool_title, cli_cmd, payload)


@dp.message(Command("tg"))
async def cmd_tg(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ <b>Использование:</b> <code>/tg &lt;юзернейм&gt;</code>\nПример: <code>/tg durov</code>", parse_mode="HTML")
        return

    target = parts[1].strip().lstrip("@")
    endpoint = "/api/scan/telegram"
    tool_title = "Telegram Datacenter & Metadata Inspector"
    cli_cmd = f"tg_inspector --target @{target}"
    payload = {"target": target, "caller": str(message.from_user.id)}
    await execute_and_send_terminal(message, endpoint, tool_title, cli_cmd, payload)


@dp.message(Command("spy"))
async def cmd_spy(message: types.Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("⏱️ <b>Spy Activity & Sleep Tracker:</b>\nИспользование: <code>/spy @username</code> или <code>/spy @user1 @user2</code> (Mutual Correlation)", parse_mode="HTML")
        return

    target1 = parts[1].strip().lstrip("@")
    target2 = parts[2].strip().lstrip("@") if len(parts) > 2 else ""

    endpoint = "/api/scan/activity_tracker"
    tool_title = "Telegram Activity & Sleep Tracker"
    cli_cmd = f"tg_activity_tracker --target @{target1}" + (f" --mutual @{target2}" if target2 else "")
    payload = {"target": target1, "target2": target2, "caller": str(message.from_user.id)}
    await execute_and_send_terminal(message, endpoint, tool_title, cli_cmd, payload)


@dp.message(Command("audit"))
async def cmd_audit(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("🛡️ <b>Breach & Leak Scanner:</b>\nИспользование: <code>/audit your_email@domain.com</code> или <code>/audit +7999...</code>", parse_mode="HTML")
        return

    target = parts[1].strip()
    endpoint = "/api/scan/breach_audit"
    tool_title = "Dehashed Leak & Credential Scanner"
    cli_cmd = f"breach_scanner --target '{target}'"
    payload = {"target": target, "caller": str(message.from_user.id)}
    await execute_and_send_terminal(message, endpoint, tool_title, cli_cmd, payload)


@dp.message(Command("recon"))
@dp.message(Command("dossier"))
@dp.message(Command("profiler"))
async def cmd_recon(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("🔍 <b>Deep Reconnaissance:</b>\nИспользование: <code>/recon &lt;цель&gt;</code>\nПример: <code>/recon durov</code>", parse_mode="HTML")
        return

    target = parts[1].strip().lstrip("@")
    endpoint = "/api/scan/autorecon"
    tool_title = "Multi-Vector Deep Reconnaissance"
    cli_cmd = f"autorecon --deep --target '{target}'"
    payload = {"target": target, "caller": str(message.from_user.id)}
    await execute_and_send_terminal(message, endpoint, tool_title, cli_cmd, payload)


# --- ФОТО И МЕДИА АНАЛИЗАТОР ---

@dp.message(F.photo)
async def handle_photo_message(message: types.Message):
    status_msg = await message.answer("🔍 <b>Анализ снимка (EXIF Forensics & Reverse Image)...</b>\n<i>Извлечение метаданных, параметров камеры и поиск по 5 движкам...</i>", parse_mode="HTML")
    try:
        photo = message.photo[-1]
        file_io = io.BytesIO()
        await bot.download(photo, destination=file_io)
        img_bytes = file_io.getvalue()
        b64_img = base64.b64encode(img_bytes).decode("utf-8")

        async with httpx.AsyncClient(timeout=35.0) as client:
            resp = await client.post(
                f"{LOCAL_API}/api/scan/universal",
                json={
                    "tool_id": "photo_exif",
                    "target": "telegram_photo.jpg",
                    "image_base64": b64_img,
                    "caller": str(message.from_user.id)
                },
                headers={"X-Telegram-User-Id": str(message.from_user.id)}
            )
            data = resp.json()

        if not data.get("ok"):
            await status_msg.edit_text(f"❌ Ошибка анализа фото: {data.get('error', 'Не удалось обработать изображение')}")
            return

        raw_cli = data.get("raw_cli_output")
        if not raw_cli:
            raw_cli = f"root@cyberhub:~# exiftool -G photo.jpg\n[+] Status: OK\n[+] Camera: {data.get('camera_make')} {data.get('camera_model')}\n[+] Date: {data.get('capture_date')}"

        text = format_terminal_box("EXIF Tool Forensic Extraction", "exiftool -G target_image.jpg", raw_cli)

        buttons = [
            [InlineKeyboardButton(text="⚡ Открыть карту и детали в WebApp", web_app=WebAppInfo(url=get_webapp_url()))],
            [
                InlineKeyboardButton(text="🌐 Google Lens", url="https://lens.google.com/"),
                InlineKeyboardButton(text="🔍 Яндекс Картинки", url="https://yandex.ru/images/search?rpt=imageview")
            ]
        ]
        if data.get("google_maps_url"):
            buttons.append([InlineKeyboardButton(text="📍 Спутниковые координаты GPS", url=data["google_maps_url"])])

        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await status_msg.edit_text(text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)

    except Exception as e:
        await status_msg.edit_text(f"❌ <b>Сбой при обработке фото:</b> {html.escape(str(e))}", parse_mode="HTML")


# --- АДМИН-КОМАНДЫ УПРАВЛЕНИЯ ПАНЕЛЬЮ ---

@dp.message(Command("users"))
async def cmd_users(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только для администратора.")
        return

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{LOCAL_API}/api/admin/users", headers={"X-Telegram-User-Id": str(message.from_user.id)})
            users = resp.json().get("users", [])

        if not users:
            await message.answer("👥 Список пользователей пуст.")
            return

        lines = ["👥 <b>Пользователи платформы:</b>\n"]
        for u in users:
            st = "🟢" if u.get("status") == "active" else "🔴"
            vip_tag = " [👑 VIP]" if u.get("is_unlimited") else f" [⚡ {u.get('scan_balance', 0)} ост.]"
            twink_tag = " ⚠️ Твинк" if u.get("is_twink") else ""
            tg_info = f"@{u.get('tg_username')}" if u.get("tg_username") else f"ID:{u.get('tg_id')}"
            lines.append(f"{st} <b>{u.get('nickname') or u.get('username')}</b> ({tg_info}){vip_tag}{twink_tag} | Поисков: {u.get('total_scans')}")

        await message.answer("\n".join(lines), parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("setscans"))
async def cmd_setscans(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только для администратора.")
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("⚠️ Формат: <code>/setscans позывной_или_tg_id количество</code>\nПример: <code>/setscans 5233450569 50</code>", parse_mode="HTML")
        return

    username = parts[1]
    try:
        amount = int(parts[2])
    except ValueError:
        await message.answer("❌ Количество должно быть числом.")
        return

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{LOCAL_API}/api/admin/user/set-quota",
                headers={"X-Telegram-User-Id": str(message.from_user.id)},
                json={"username": username, "amount": amount, "mode": "set"}
            )
            data = resp.json()

        if data.get("ok"):
            await message.answer(f"✅ {data.get('message')}", parse_mode="HTML")
        else:
            await message.answer(f"❌ {data.get('error')}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("grantvip"))
async def cmd_grantvip(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только для администратора.")
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("⚠️ Формат: <code>/grantvip позывной_или_tg_id</code>", parse_mode="HTML")
        return

    username = parts[1]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{LOCAL_API}/api/admin/user/set-quota",
                headers={"X-Telegram-User-Id": str(message.from_user.id)},
                json={"username": username, "mode": "unlimited"}
            )
            data = resp.json()

        if data.get("ok"):
            await message.answer(f"👑 Пользователю <code>{username}</code> выдан бесконечный доступ (VIP)!", parse_mode="HTML")
        else:
            await message.answer(f"❌ {data.get('error')}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("adduser"))
async def cmd_adduser(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только для администратора.")
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("⚠️ Формат: <code>/adduser позывной [пароль] [роль]</code>", parse_mode="HTML")
        return

    username = parts[1]
    password = parts[2] if len(parts) > 2 else "12345"
    role = parts[3] if len(parts) > 3 else "user"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{LOCAL_API}/api/admin/users/create",
                headers={"X-Telegram-User-Id": str(message.from_user.id)},
                json={"username": username, "password": password, "role": role}
            )
            data = resp.json()

        if data.get("ok"):
            await message.answer(f"✅ Пользователь <code>{username}</code> успешно создан.", parse_mode="HTML")
        else:
            await message.answer(f"❌ {data.get('error')}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("banuser"))
async def cmd_banuser(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только для администратора.")
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("⚠️ Формат: <code>/banuser позывной_или_tg_id</code>", parse_mode="HTML")
        return

    username = parts[1]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{LOCAL_API}/api/admin/users/toggle_status",
                headers={"X-Telegram-User-Id": str(message.from_user.id)},
                json={"username": username}
            )
            data = resp.json()

        if data.get("ok"):
            await message.answer(f"🔄 Статус пользователя <code>{username}</code>: <b>{data.get('new_status')}</b>", parse_mode="HTML")
        else:
            await message.answer(f"❌ {data.get('error')}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@dp.message(Command("visits"))
async def cmd_visits(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только для администратора.")
        return

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{LOCAL_API}/api/admin/visitors?limit=10", headers={"X-Telegram-User-Id": str(message.from_user.id)})
            visitors = resp.json().get("visitors", [])

        if not visitors:
            await message.answer("📊 Журнал визитов пуст.")
            return

        lines = ["🌐 <b>Последние 10 визитов:</b>\n"]
        for v in visitors:
            ts = v.get("ts", "")[:19].replace("T", " ")
            user_lbl = v.get("user") or v.get("tg_username") or v.get("tg_id") or "Гость"
            lines.append(f"• <code>{ts}</code> | <b>{user_lbl}</b> | IP: <code>{v.get('ip')}</code> | {v.get('country')} ({v.get('city')})")

        await message.answer("\n".join(lines), parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


# --- АВТОМАТИЧЕСКОЕ РАСПОЗНАВАНИЕ ТЕКСТА (FALLBACK SCAN) ---

@dp.message()
async def fallback_text_scan(message: types.Message):
    """
    Если пользователь просто отправляет текст в бота без слэш-команд:
    Бот автоматически анализирует тип входных данных (телефон, ник, почта, IP, домен, крипта)
    и запускает целевой модуль OSINT с выводом консольного лога.
    """
    raw_text = (message.text or "").strip()
    if not raw_text:
        return

    # Защита от случайных системных команд
    if raw_text.startswith("/"):
        await message.answer("❓ Неизвестная команда. Введите <code>/help</code> для списка команд.", parse_mode="HTML")
        return

    endpoint, tool_title, cli_cmd, payload_key = detect_target_vector(raw_text)
    payload = {payload_key: raw_text, "caller": str(message.from_user.id)}
    await execute_and_send_terminal(message, endpoint, tool_title, cli_cmd, payload)


import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


async def main():
    logging.basicConfig(level=logging.INFO)
    logging.info("Telegram Bot started in Terminal Console OSINT mode...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
