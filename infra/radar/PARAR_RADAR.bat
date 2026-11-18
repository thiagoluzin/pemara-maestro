@echo off
chcp 65001 >nul
title Pemara Tech - Parar Radar Monitor
color 0C

echo ============================================================
echo   PARANDO RADAR MONITOR - PEMARA TECH
echo ============================================================
echo.

:: Verifica privilégios de administrador
net session >nul 2>&1
if not %errorlevel% == 0 (
    echo Solicitando privilégios de Administrador...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Para a tarefa agendada
schtasks /query /TN "Pemara_Radar" >nul 2>&1
if %errorlevel% == 0 (
    echo [1/2] Parando tarefa agendada 'Pemara_Radar'...
    schtasks /end /TN "Pemara_Radar" >nul 2>&1
)

:: Encerra o processo python associado ao radar_monitor.py de forma forçada
echo [2/2] Encerrando processos locais do Radar Monitor...
powershell -Command "Get-CimInstance Win32_Process | Where-Object CommandLine -like '*radar_monitor.py*' | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

echo.
echo [OK] Radar Monitor parado com sucesso.
echo.
ping 127.0.0.1 -n 4 >nul
