@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Trocar senha do Maestro Pro

cd /d "%~dp0"

if /I not "%~1"=="--self-test" goto normal_start
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\reset_maestro_admin_password.ps1" -SelfTest
exit /b %ERRORLEVEL%

:normal_start

if not exist "%~dp0tools\reset_maestro_admin_password.ps1" (
    echo ERRO: auxiliar de troca de senha nao encontrado.
    echo Caminho esperado: %~dp0tools\reset_maestro_admin_password.ps1
    pause
    exit /b 2
)

where python.exe >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao foi encontrado no PATH.
    pause
    exit /b 3
)

fltmc.exe >nul 2>&1
if errorlevel 1 (
    echo Solicitando permissao de administrador...
    set "MAESTRO_RESET_BAT=%~f0"
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath $env:MAESTRO_RESET_BAT -Verb RunAs"
    if errorlevel 1 (
        echo ERRO: a elevacao foi cancelada ou falhou.
        pause
        exit /b 4
    )
    exit /b 0
)

echo.
echo ==============================================
echo       TROCAR SENHA DO MAESTRO PRO
echo ==============================================
echo A senha sera solicitada duas vezes e nao aparecera na tela.
echo Nenhuma senha em texto puro sera salva.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\reset_maestro_admin_password.ps1"
set "RESET_EXIT=%ERRORLEVEL%"

echo.
if "%RESET_EXIT%"=="0" (
    echo Processo concluido. Use a nova senha na tela do Maestro.
) else (
    echo A troca nao foi concluida. A configuracao anterior foi preservada ou restaurada.
)
echo.
pause
exit /b %RESET_EXIT%
