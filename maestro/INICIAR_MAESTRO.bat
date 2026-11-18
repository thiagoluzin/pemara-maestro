@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File E:\Pemara\radar\pemara_boot_watchdog.ps1 -Once
exit /b %ERRORLEVEL%
