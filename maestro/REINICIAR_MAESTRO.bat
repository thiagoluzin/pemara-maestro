@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File E:\Pemara\maestro\pemara\solicitar_reinicio_maestro.ps1 -Componente all
exit /b %ERRORLEVEL%
