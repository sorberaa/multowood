# -*- coding: utf-8 -*-
"""
Каталог функций Multiwood — структурированный список возможностей мультитула.
Отдаётся через GET /api/catalog как {"ok": True, "groups": CATALOG}.
"""

CATALOG = [
    {
        "id": "downloader",
        "title": "📥 Скачивание медиа",
        "desc": "Видео и аудио из соцсетей без водяных знаков.",
        "tools": [
            {
                "id": "video_dl",
                "name": "📥 Скачать видео MP4",
                "purpose": "TikTok, Instagram Reels, YouTube Shorts, X, Pinterest, VK — чистое видео высокого качества.",
                "input": "ссылка на видео",
                "launch": {"type": "bot", "label": "Отправьте ссылку в чат", "action": "send_url"},
            },
            {
                "id": "audio_dl",
                "name": "🎵 Извлечь аудио MP3",
                "purpose": "Превращает любое видео в аудиофайл без потери качества.",
                "input": "ссылка на видео",
                "launch": {"type": "bot", "label": "Кнопка «Извлечь MP3»", "action": "auto_mp3"},
            },
        ],
    },
    {
        "id": "daily",
        "title": "🌦 Ежедневные функции",
        "desc": "То, зачем открывают бота каждый день.",
        "tools": [
            {
                "id": "weather",
                "name": "🌦 Погода и прогноз",
                "purpose": "Погода сейчас и прогноз на 4 дня для любого города мира (open-meteo).",
                "input": "название города",
                "launch": {"type": "bot", "label": "/weather Москва", "action": "weather"},
                "web_runnable": True,
            },
            {
                "id": "currency",
                "name": "💱 Курсы валют",
                "purpose": "Актуальные курсы популярных валют и мгновенная конвертация суммы.",
                "input": "сумма и коды валют: 100 USD RUB",
                "launch": {"type": "bot", "label": "/cur 100 USD RUB", "action": "currency"},
                "web_runnable": True,
            },
            {
                "id": "pwcheck",
                "name": "🛡 Проверка пароля на утечки",
                "purpose": "Проверяет пароль по базе HaveIBeenPwned. Пароль не передаётся — только 5-символьный префикс SHA-1 (k-анонимность).",
                "input": "пароль для проверки",
                "launch": {"type": "bot", "label": "/check пароль", "action": "check_password"},
                "web_runnable": True,
            },
            {
                "id": "shortener",
                "name": "🔗 Короткие ссылки",
                "purpose": "Сокращает длинные URL и считает переходы по короткой ссылке.",
                "input": "длинная ссылка",
                "launch": {"type": "bot", "label": "/short ссылка", "action": "shorten"},
                "web_runnable": True,
            },
            {
                "id": "unit_convert",
                "name": "📐 Конвертер единиц",
                "purpose": "Длина, вес, объём, скорость, объём данных и температура — офлайн и мгновенно.",
                "input": "значение и единицы: 100 km mi",
                "launch": {"type": "bot", "label": "/convert 100 km mi", "action": "convert_unit"},
                "web_runnable": True,
            },
            {
                "id": "wifi_qr",
                "name": "📶 Wi-Fi QR-код",
                "purpose": "QR для мгновенного подключения к Wi-Fi без ввода пароля.",
                "input": "имя сети и пароль",
                "launch": {"type": "bot", "label": "/wifi Сеть пароль", "action": "wifi_qr"},
                "web_runnable": True,
            },
            {
                "id": "photo_compress",
                "name": "🗜 Сжатие фото",
                "purpose": "Уменьшает размер фото без заметной потери качества — экономия трафика и памяти.",
                "input": "изображение (JPEG/PNG)",
                "launch": {"type": "bot", "label": "Просто отправьте фото боту", "action": "compress"},
                "web_runnable": True,
            },
        ],
    },

    {
        "id": "utilities",
        "title": "🛠 Мобильные утилиты",
        "desc": "Быстрые инструменты для повседневных задач.",
        "tools": [
            {
                "id": "tempmail",
                "name": "📬 Временная почта",
                "purpose": "Одноразовый ящик для регистраций без спама (живой сервис mail.tm).",
                "input": "—",
                "launch": {"type": "bot", "label": "/mail", "action": "tempmail"},
                "web_runnable": True,
            },
            {
                "id": "password_gen",
                "name": "🔐 Генератор паролей",
                "purpose": "Стойкие пароли с расчётом энтропии в битах.",
                "input": "длина (8-40)",
                "launch": {"type": "bot", "label": "/pass 18", "action": "password"},
                "web_runnable": True,
            },
            {
                "id": "qr_gen",
                "name": "📷 QR-коды",
                "purpose": "QR для ссылок, текстов и Wi-Fi — с сохранением изображения.",
                "input": "текст или ссылка",
                "launch": {"type": "bot", "label": "/qr текст", "action": "qr"},
                "web_runnable": True,
            },
            {
                "id": "link_cleaner",
                "name": "🪄 Очистка ссылок",
                "purpose": "Удаляет UTM-метки и трекеры (utm_, fbclid, gclid, igsh...) из URL.",
                "input": "ссылка с трекерами",
                "launch": {"type": "bot", "label": "/clean ссылка", "action": "clean"},
                "web_runnable": True,
            },
            {
                "id": "hash",
                "name": "🔐 Хэши текста",
                "purpose": "MD5, SHA1 и SHA256 любого текста мгновенно.",
                "input": "любой текст",
                "launch": {"type": "bot", "label": "/hash текст", "action": "hash"},
            },
            {
                "id": "ai_summary",
                "name": "🧠 AI-выжимка",
                "purpose": "Главные тезисы статьи или длинного текста за пару секунд.",
                "input": "ссылка на статью или текст",
                "launch": {"type": "bot", "label": "/sum ссылка", "action": "summarize"},
                "web_runnable": True,
            },
            {
                "id": "decode",
                "name": "🧩 Декодер",
                "purpose": "Base64, URL-encode, hex и другие декодирования одной кнопкой.",
                "input": "закодированная строка",
                "web_runnable": True,
            },
        ],
    },
    {
        "id": "gamification",
        "title": "🎮 Прогресс и награды",
        "desc": "Система вовлечения: XP, уровни и ежедневные бонусы.",
        "tools": [
            {
                "id": "profile",
                "name": "👤 Профиль и уровень",
                "purpose": "XP-прогресс, статистика действий и отображаемый ник.",
                "input": "—",
                "launch": {"type": "bot", "label": "/profile", "action": "profile"},
            },
            {
                "id": "daily_bonus",
                "name": "🎁 Ежедневный бонус",
                "purpose": "+15 XP каждый день с нарастающей серией посещений.",
                "input": "—",
                "launch": {"type": "bot", "label": "/daily", "action": "daily"},
            },
            {
                "id": "leaderboard",
                "name": "🏆 Таблица лидеров",
                "purpose": "Топ-10 пользователей по XP с медалями и ролями.",
                "input": "—",
                "launch": {"type": "bot", "label": "/top", "action": "top"},
            },
        ],
    },
]
