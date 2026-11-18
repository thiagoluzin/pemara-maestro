@echo off
chcp 65001 >nul
title Pemara Tech - Status do Radar Monitor
color 0A
echo.
echo  [PEMARA TECH] STATUS DO RADAR MONITOR
echo.

powershell -Command "try { $socket = New-Object System.Net.Sockets.TcpClient('127.0.0.1', 49999); $socket.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% == 0 (
    echo  Radar Monitor: [ATIVO / RODANDO]
) else (
    echo  Radar Monitor: [INATIVO / PARADO]
)
echo.
echo  ==================== LOGS EM TEMPO REAL ====================
echo  Pressione Ctrl+C para sair.
echo.

if exist "E:\Pemara\logs\radar_monitor.log" (
    powershell -Command "Get-Content -Path E:\Pemara\logs\radar_monitor.log -Tail 20 -Wait"
) else (
    echo [!] Arquivo de log ainda nao criado. O Radar precisa iniciar para gerar os logs.
    echo.
    pause
)
