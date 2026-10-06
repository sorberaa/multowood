@echo off
chcp 65001 > nul
title CYBER MULTITOOL // @Multiwood_bot
echo ========================================================
echo  CYBER MULTITOOL PRO // @Multiwood_bot LAUNCHER
echo ========================================================
echo.
echo [*] Запуск WebApp API на порту 8000...
start /B "" "d:\osint-bot\.venv\Scripts\python.exe" "d:\osint-bot\src\webapp.py"
timeout /t 2 > nul

echo [*] Запуск Telegram Bot @Multiwood_bot...
"d:\osint-bot\.venv\Scripts\python.exe" "d:\osint-bot\src\bot.py"

pause
