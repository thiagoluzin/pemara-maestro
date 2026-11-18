@echo off
chcp 65001 >nul
title Instalar Radar Monitor - Pemara Tech
color 0B

echo ============================================================
echo   INSTALADOR DO RADAR MONITOR - PEMARA TECH
echo ============================================================
echo.
echo Solicitando permissões de Administrador para registrar a tarefa...
echo.

:: Verifica privilégios de administrador
net session >nul 2>&1
if %errorlevel% == 0 (
    goto :run
) else (
    :: Solicita elevação via PowerShell RunAs
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:run
echo [1/2] Registrando tarefa no Agendador de Tarefas do Windows...
powershell -ExecutionPolicy Bypass -Command "$action = New-ScheduledTaskAction -Execute 'C:\Program Files\Python311\python.exe' -Argument 'E:\Pemara\radar\radar_monitor.py' -WorkingDirectory 'E:\Pemara\radar'; $trigger = New-ScheduledTaskTrigger -AtStartup; $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 365) -Compatibility Win8 -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1); $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType Service -RunLevel Highest; Register-ScheduledTask -TaskName 'Pemara_Radar' -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Agente de monitoramento e recuperacao Pemara Tech' -Force" > E:\Pemara\logs\instalacao_radar.log 2>&1

if %errorlevel% == 0 (
    echo.
    echo ============================================================
    echo   [OK] RADAR MONITOR INSTALADO COM SUCESSO!
    echo ============================================================
    echo   A partir de agora, o Radar Monitor iniciará automaticamente
    echo   quando o computador ligar (antes de qualquer logon).
    echo ============================================================
) else (
    echo.
    echo [ERRO] Falha ao registrar a tarefa no Agendador de Tarefas.
)
echo.
echo Concluído.
timeout /t 3
