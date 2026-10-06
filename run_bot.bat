@echo off
chcp 65001 > nul
title CYBER MULTITOOL // @Multiwood_bot
echo ========================================================
echo  CYBER MULTITOOL PRO // @Multiwood_bot LAUNCHER
echo ========================================================
echo.

set "ROOT=%~dp0"
set "PY=%ROOT%.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo [*] Запуск WebApp API на порту 8000...
start /B "" "%PY%" "%ROOT%src\webapp.py"
timeout /t 2 > nul

echo [*] Запуск Telegram Bot @Multiwood_bot...
"%PY%" "%ROOT%src\bot.py"

pause
