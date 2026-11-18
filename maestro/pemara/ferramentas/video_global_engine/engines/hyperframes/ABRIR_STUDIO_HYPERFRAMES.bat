@echo off
setlocal
cd /d "%~dp0"
set "HYPERFRAMES_NO_UPDATE_CHECK=1"
call npm run preview:pilot
exit /b %ERRORLEVEL%
