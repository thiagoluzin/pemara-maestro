@echo off
setlocal EnableExtensions
chcp 65001 >nul
call :resolve
call :python --action install --component h3 --accept-licenses %*
goto :finish
:resolve
if not defined PEMARA_ROOT if exist "%~dp0..\..\..\..\maestro\pemara\services\studio\h3_workflow.py" set "PEMARA_ROOT=%~dp0..\..\..\.."
if not defined PEMARA_ROOT set "PEMARA_ROOT=E:\Pemara"
exit /b 0
:python
where py >nul 2>&1
if errorlevel 1 goto python_exe
py -3.11 "%~dp0install_models.py" --target-root "%PEMARA_ROOT%" %*
exit /b %errorlevel%
:python_exe
where python >nul 2>&1
if errorlevel 1 echo ERRO: Python 3.11 ou superior nao encontrado. & exit /b 1
python "%~dp0install_models.py" --target-root "%PEMARA_ROOT%" %*
exit /b %errorlevel%
:finish
set "RC=%errorlevel%"
if "%RC%"=="0" echo Processo H3 concluido.
if not "%RC%"=="0" echo FALHOU. Consulte os logs em %PEMARA_ROOT%\logs\model_installers.
if not defined PEMARA_NO_PAUSE pause
exit /b %RC%
