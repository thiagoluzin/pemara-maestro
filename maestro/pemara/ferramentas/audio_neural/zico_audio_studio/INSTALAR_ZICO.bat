@echo off
chcp 65001 >nul
title ZICO Audio Studio - Instalador
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\install.ps1"
pause
