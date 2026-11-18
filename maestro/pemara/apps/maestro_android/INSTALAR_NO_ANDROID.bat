@echo off
setlocal

set "ADB=%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"
set "APK=%~dp0dist\MaestroStudio-1.0.0-beta.11.apk"

if not exist "%ADB%" (
  echo Android ADB nao encontrado em: %ADB%
  exit /b 1
)

if not exist "%APK%" (
  echo APK nao encontrado em: %APK%
  exit /b 1
)

echo Verificando telefone conectado...
"%ADB%" devices
echo.
echo Instalando Maestro Studio beta...
"%ADB%" install -r "%APK%"
if errorlevel 1 (
  echo.
  echo A instalacao falhou. Confirme o USB debugging e autorize esta maquina no telefone.
  exit /b 1
)

echo.
echo Maestro Studio instalado com sucesso.
endlocal
