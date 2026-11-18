@echo off
setlocal EnableExtensions
chcp 65001 >nul
if not defined PEMARA_ROOT set "PEMARA_ROOT=E:\Pemara"
where py >nul 2>&1
if errorlevel 1 goto python_exe
py -3.11 "%~dp0install_rife425.py" --target-root "%PEMARA_ROOT%" --accept-license %*
exit /b %errorlevel%
:python_exe
python "%~dp0install_rife425.py" --target-root "%PEMARA_ROOT%" --accept-license %*
exit /b %errorlevel%
