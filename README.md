# 🎯 Multiwood — Мультитул + OSINT-бот (образовательный)

Telegram-бот и FastAPI-бэкенд со **скачиванием медиа без водяных знаков**, мобильными утилитами, **OSINT-модулями** (только публичные данные), **системой аккаунтов** (XP / уровни / роли) и **админ-панелью** (пользователи, визиты, рассылки).

> ⚠️ **Образовательный проект.** Живой запуск утилит против людей **без согласия** запрещён. Используйте только публичные данные и соблюдайте закон вашей страны.

## 📦 Возможности

### 📥 Скачивание медиа (без водяных знаков)
TikTok, Instagram Reels, YouTube Shorts, X, Pinterest, VK — пришлите ссылку в чат или откройте Mini App. Видео **MP4** или аудио **MP3**.

### 🛠 Мобильные утилиты
Временная почта (живой **mail.tm**), генератор паролей (энтропия в битах), QR-коды, очистка ссылок от трекеров, AI-выжимка статей.

### 🔍 OSINT-модули (учебные, публичные данные)
| Модуль | Что делает |
|---|---|
| `/username` | Поиск аккаунта на 60+ сайтах (база Sherlock, реальные HTTP-проверки) |
| `/phone` | Оператор, регион, тип номера (phonenumbers, офлайн) |
| `/ip` | Страна, город, провайдер, координаты (резервные публичные API) |
| `/domain` | DNS (IP), HTTP/HTTPS/HSTS-проба |
| `/email` | MX-записи, бесплатные/временные провайдеры |
| Telegram / GitHub | Публичные профили t.me и api.github.com |
| `/dorks` | Генератор учебных Google-dorks |
| Автодосье | Автодетект цели → комбинация модулей |
| Атрибуция | Детектор «корневого» хэндла (виртуальные аккаунты) |

### 🎮 Система аккаунтов
- Профиль: ник, роль (`user` / `vip` / `admin`), уровень и XP-прогресс
- Ежедневный бонус `/daily` с серией дней 🔥
- Таблица лидеров `/top`
- Счётчики: скачивания, почта, сканы
- Бан действует **и в боте, и в вебе**; админа забанить нельзя

### 🛡 Админ-панель (веб + команды бота)
- **Статистика**: пользователи, активные сегодня, скачивания/сканы, визиты, баны/VIP, диск
- **Пользователи**: таблица, бан/разбан и VIP одним кликом
- **Журнал IP-визитов**: IP, страна, путь, User-Agent (+ `/admin/visits-html?token=...`)
- **Рассылка** с автоматическим HTML-фоллбэком
- Команды бота: `/admin`, `/visits`, `/users`, `/bc текст`, `/ban id`, `/unban id`

## 🚀 Быстрый старт

### Windows (локально)
```bat
run_bot.bat
```

### Docker
```bash
cp config/.env.example config/.env   # заполнить BOT_TOKEN, ADMIN_CHAT_ID, ADMIN_TOKEN, DOMAIN
mkdir -p data
docker compose up -d --build
# http://localhost:8000
```

## ⚙️ Конфигурация (config/.env)
```env
BOT_TOKEN=123456789:ABC...        # от @BotFather
ADMIN_CHAT_ID=987654321           # ваш Telegram ID
ADMIN_TOKEN=long_random_token     # доступ к /admin/visits-html
DOMAIN=https://your-domain.com    # HTTPS обязателен для WebApp
DATA_DIR=/app/data                # папка данных (users.json, visitors.json)
```

## 📖 Команды бота

| Команда | Описание |
|---|---|
| `/start` `/help` | Меню и инструкция |
| `/dl <ссылка>` | Скачать видео/аудио (или просто пришлите ссылку) |
| `/profile` `/nick` | Профиль и смена ника |
| `/daily` `/top` | Бонус XP и таблица лидеров |
| `/username` `/phone` `/ip` `/domain` `/dorks` | OSINT-модули |
| `/mail` `/pass` `/qr` `/clean` `/hash` `/sum` | Утилиты |
| `/admin` `/visits` `/users` `/bc` `/ban` `/unban` | Админ-инструменты |

## 🧪 Тесты и аудит

```bash
python src/webapp.py               # 1) запустить сервер
python scripts/test_all_endpoints.py   # 2) 12 интеграционных тестов
python scripts/audit_all_modules.py    # аудит 19 модулей
python scripts/debug_osint.py          # диагностика OSINT-движка
```

## 📂 Структура проекта
```
multowood/
├── src/
│   ├── bot.py          # Telegram-бот (aiogram 3)
│   ├── webapp.py       # FastAPI-бэкенд + админ-API
│   ├── accounts.py     # система аккаунтов (роли, XP, баны)
│   ├── osint.py        # OSINT-движок
│   ├── multitool.py    # медиа, почта, утилиты
│   └── catalog.py      # каталог утилит
├── index.html          # Mini App (SPA)
├── data/               # users.json, visitors.json, sherlock-базы
├── scripts/            # тесты и аудит
├── config/.env.example
├── Dockerfile · docker-compose.yml · entrypoint.sh
└── run_bot.bat         # локальный запуск Windows
```

## 🛡 Безопасность
- Проверка Telegram WebApp initData (HMAC-SHA256)
- Анти-SSRF и валидация входных данных в сканерах
- `config/.env` и `data/*` не попадают в Git
- Роль admin назначается **только** по `ADMIN_CHAT_ID` — через API её не получить

## ⚖️ Правовая информация
Образовательный проект. Не используйте для шпионажа, преследования или хакинга. Уважайте приватность людей и соблюдайте закон.

## 📄 Лицензия
MIT License
