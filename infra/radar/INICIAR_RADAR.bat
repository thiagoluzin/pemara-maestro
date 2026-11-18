@echo off
chcp 65001 >nul
title Pemara Tech - Iniciar Radar Monitor
color 0B

echo ============================================================
echo   INICIANDO RADAR MONITOR - PEMARA TECH
echo ============================================================
echo.

:: Verifica privilégios de administrador
net session >nul 2>&1
if not %errorlevel% == 0 (
    echo Solicitando privilégios de Administrador...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Verifica se já está rodando via porta lock 49999
powershell -Command "try { $socket = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 49999); $socket.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% == 0 (
    echo [!] O Radar Monitor já está em execução!
    echo.
    ping 127.0.0.1 -n 4 >nul
    exit /b
)

cd /d "%~dp0"

:: Tenta iniciar via Agendador de Tarefas se a tarefa existir
schtasks /query /TN "Pemara_Radar" >nul 2>&1
if %errorlevel% == 0 (
    echo [1/2] Iniciando tarefa agendada 'Pemara_Radar' (rodando sob SYSTEM)...
    schtasks /run /TN "Pemara_Radar" >nul
) else (
    echo [!] Tarefa agendada 'Pemara_Radar' não encontrada.
    echo [1/2] Iniciando Radar Monitor localmente em segundo plano...
    powershell -Command "Start-Process python -ArgumentList 'radar_monitor.py' -WindowStyle Hidden"
)

echo.
echo [OK] Radar Monitor iniciado com sucesso.
echo.
ping 127.0.0.1 -n 4 >nul
