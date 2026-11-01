@echo off
title H143 Proxy Checker Bot
color 0b
cd /d "%~dp0"

echo ==========================================================
echo        H143 PROXY CHECKER TELEGRAM BOT LAUNCHER
echo ==========================================================
echo.

:: Check if virtual environment exists
if not exist "venv\Scripts\python.exe" (
    echo [INFO] Creating Python virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv. Please ensure Python is installed.
        pause
        exit /b 1
    )
    echo [INFO] Installing required dependencies...
    venv\Scripts\pip.exe install -r requirements.txt
)

:: Check if .env exists
if not exist ".env" (
    copy .env.example .env >nul
)

:: Check if BOT_TOKEN is empty in .env
findstr /C:"BOT_TOKEN=" .env | findstr /V /C:"BOT_TOKEN= " >nul
for /f "tokens=1,* delims==" %%A in ('findstr /B "BOT_TOKEN=" .env') do set "TOKEN_VAL=%%B"

if "%TOKEN_VAL%"=="" (
    echo [ATTENTION] Bot Token is not set in .env!
    echo.
    echo Telegram @BotFather theke apnar Bot Token copy kore ekhane paste korun:
    set /p USER_TOKEN="Enter Telegram Bot Token: "
    if not "%USER_TOKEN%"=="" (
        powershell -Command "(Get-Content .env) -replace '^BOT_TOKEN=.*', 'BOT_TOKEN=%USER_TOKEN%' | Set-Content .env"
        echo [SUCCESS] Token saved to .env!
        echo.
    ) else (
        echo [WARNING] No token entered. Please edit .env file manually.
        pause
        exit /b 1
    )
)

echo [INFO] Starting H143 Proxy Checker Bot...
echo.
venv\Scripts\python.exe bot.py

echo.
echo ==========================================================
echo Bot has stopped. Press any key to exit.
echo ==========================================================
pause

