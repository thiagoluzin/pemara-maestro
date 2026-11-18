@echo off
setlocal
cd /d "%~dp0"
set "HYPERFRAMES_NO_UPDATE_CHECK=1"
call npm run check:pilot
if errorlevel 1 exit /b %ERRORLEVEL%
call npm run render:pilot
exit /b %ERRORLEVEL%
