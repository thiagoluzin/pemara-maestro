@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem =============================================================================
rem  build_wheel.bat - Build sageattention (v2 / v2++) wheel for Windows
rem
rem  Requirements:
rem    - Visual Studio 2022/2026 Build Tools (MSVC) with C++ workload
rem    - CUDA Toolkit >= 12.0 (12.8+ for Blackwell / RTX 50; 13.x recommended)
rem    - Python with matching torch CUDA build installed
rem    - ninja, packaging, wheel, build (pip packages)
rem
rem  Usage:
rem    build_wheel.bat
rem    build_wheel.bat --clean
rem    build_wheel.bat --python "D:\path\to\python.exe"
rem    build_wheel.bat --cuda "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.2"
rem    build_wheel.bat --jobs 2
rem =============================================================================

cd /d "%~dp0"

rem Prefer local uv/venv, then PATH python.
set "PY_EXE=python"
if exist "%~dp0.venv\Scripts\python.exe" (
  set "PY_EXE=%~dp0.venv\Scripts\python.exe"
)
set "CUDA_HOME_OVERRIDE="
set "DO_CLEAN=0"
set "MAX_JOBS=2"
set "ARCH_LIST_OVERRIDE="

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--clean" (
  set "DO_CLEAN=1"
  shift
  goto parse_args
)
if /I "%~1"=="--python" (
  set "PY_EXE=%~2"
  shift
  shift
  goto parse_args
)
if /I "%~1"=="--cuda" (
  set "CUDA_HOME_OVERRIDE=%~2"
  shift
  shift
  goto parse_args
)
if /I "%~1"=="--jobs" (
  set "MAX_JOBS=%~2"
  shift
  shift
  goto parse_args
)
if /I "%~1"=="--arch" (
  set "ARCH_LIST_OVERRIDE=%~2"
  shift
  shift
  goto parse_args
)
if /I "%~1"=="--help" (
  call :print_help
  exit /b 0
)
if /I "%~1"=="-h" (
  call :print_help
  exit /b 0
)
echo [ERROR] Unknown argument: %~1
call :print_help
exit /b 1

:print_help
echo.
echo Usage: build_wheel.bat [options]
echo.
echo Options:
echo   --clean                 Remove build\ and dist\ before compiling
echo   --python PATH           Python executable to use
echo   --cuda PATH             CUDA Toolkit root (sets CUDA_HOME)
echo   --jobs N                Parallel compile jobs (default: 2)
echo   --arch LIST             TORCH_CUDA_ARCH_LIST (e.g. "12.0" or "8.9;12.0")
echo   --help                  Show this help
echo.
goto :eof

:args_done

echo.
echo ============================================================
echo  SageAttention 2.x - Windows wheel build
echo ============================================================
echo.

rem ----- Locate Visual Studio / MSVC -----
set "VCVARS="
if defined VSINSTALLDIR (
  if exist "%VSINSTALLDIR%\VC\Auxiliary\Build\vcvars64.bat" (
    set "VCVARS=%VSINSTALLDIR%\VC\Auxiliary\Build\vcvars64.bat"
  )
)

rem Prefer VS 2026 (folder "18" / "2026"), then vswhere, then older years.
if not defined VCVARS (
  for %%E in (BuildTools Community Professional Enterprise) do (
    if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\18\%%E\VC\Auxiliary\Build\vcvars64.bat" (
      set "VCVARS=%ProgramFiles(x86)%\Microsoft Visual Studio\18\%%E\VC\Auxiliary\Build\vcvars64.bat"
    )
    if exist "%ProgramFiles%\Microsoft Visual Studio\18\%%E\VC\Auxiliary\Build\vcvars64.bat" (
      set "VCVARS=%ProgramFiles%\Microsoft Visual Studio\18\%%E\VC\Auxiliary\Build\vcvars64.bat"
    )
    if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\2026\%%E\VC\Auxiliary\Build\vcvars64.bat" (
      set "VCVARS=%ProgramFiles(x86)%\Microsoft Visual Studio\2026\%%E\VC\Auxiliary\Build\vcvars64.bat"
    )
    if exist "%ProgramFiles%\Microsoft Visual Studio\2026\%%E\VC\Auxiliary\Build\vcvars64.bat" (
      set "VCVARS=%ProgramFiles%\Microsoft Visual Studio\2026\%%E\VC\Auxiliary\Build\vcvars64.bat"
    )
  )
)

if not defined VCVARS if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" (
  for /f "usebackq delims=" %%i in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do (
    if exist "%%i\VC\Auxiliary\Build\vcvars64.bat" set "VCVARS=%%i\VC\Auxiliary\Build\vcvars64.bat"
  )
)

if not defined VCVARS (
  for %%Y in (2026 18 2025 2022) do (
    for %%E in (BuildTools Community Professional Enterprise) do (
      if exist "%ProgramFiles%\Microsoft Visual Studio\%%Y\%%E\VC\Auxiliary\Build\vcvars64.bat" (
        set "VCVARS=%ProgramFiles%\Microsoft Visual Studio\%%Y\%%E\VC\Auxiliary\Build\vcvars64.bat"
      )
      if exist "%ProgramFiles(x86)%\Microsoft Visual Studio\%%Y\%%E\VC\Auxiliary\Build\vcvars64.bat" (
        set "VCVARS=%ProgramFiles(x86)%\Microsoft Visual Studio\%%Y\%%E\VC\Auxiliary\Build\vcvars64.bat"
      )
    )
  )
)

if not defined VCVARS (
  echo [ERROR] Could not find vcvars64.bat.
  echo         Install Visual Studio Build Tools with "Desktop development with C++".
  exit /b 1
)

echo [INFO] Loading MSVC environment:
echo        %VCVARS%
call "%VCVARS%"
if errorlevel 1 (
  echo [ERROR] vcvars64.bat failed.
  exit /b 1
)

where cl >nul 2>&1
if errorlevel 1 (
  echo [ERROR] cl.exe not found after vcvars64. Check your MSVC install.
  exit /b 1
)

rem ----- Python -----
for %%P in ("%PY_EXE%") do set "PY_EXE=%%~fP"
if not exist "%PY_EXE%" (
  where "%PY_EXE%" >nul 2>&1
  if errorlevel 1 (
    echo [ERROR] Python not found: %PY_EXE%
    exit /b 1
  )
)

echo [INFO] Python:
"%PY_EXE%" -c "import sys; print(sys.executable); print(sys.version)"
if errorlevel 1 exit /b 1

rem Put this interpreter's Scripts dir on PATH (ninja.exe from uv/pip install ninja).
set "PY_SCRIPTS="
"%PY_EXE%" -c "import sysconfig; print(sysconfig.get_path('scripts'))" > "%TEMP%\sageattn_scripts.txt" 2>nul
if exist "%TEMP%\sageattn_scripts.txt" (
  set /p PY_SCRIPTS=<"%TEMP%\sageattn_scripts.txt"
  del "%TEMP%\sageattn_scripts.txt" >nul 2>&1
)
if defined PY_SCRIPTS (
  set "PATH=%PY_SCRIPTS%;%PATH%"
  echo [INFO] Python Scripts: %PY_SCRIPTS%
)

"%PY_EXE%" -c "import torch; print('torch', torch.__version__, 'cuda', torch.version.cuda)"
if errorlevel 1 (
  echo [ERROR] PyTorch is required. Install a CUDA-enabled torch first.
  exit /b 1
)

rem "%PY_EXE%" -c "import torch; assert torch.cuda.is_available(), 'CUDA GPU not visible to torch'; 
print('GPU', torch.cuda.get_device_name(0), 'capability', torch.cuda.get_device_capability(0))"
rem if errorlevel 1 (
rem   echo [WARN] GPU not visible. You can still build if you pass --arch "12.0" (or similar).
rem )

rem ----- CUDA Toolkit -----
if defined CUDA_HOME_OVERRIDE set "CUDA_HOME=%CUDA_HOME_OVERRIDE%"

if not defined CUDA_HOME (
  if exist "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.2\bin\nvcc.exe" set "CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.2"
)
if not defined CUDA_HOME (
  if exist "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1\bin\nvcc.exe" set "CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1"
)
if not defined CUDA_HOME (
  if exist "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.0\bin\nvcc.exe" set "CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.0"
)
if not defined CUDA_HOME (
  if exist "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.9\bin\nvcc.exe" set "CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.9"
)
if not defined CUDA_HOME (
  if exist "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8\bin\nvcc.exe" set "CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8"
)
if not defined CUDA_HOME (
  if exist "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin\nvcc.exe" set "CUDA_HOME=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4"
)

if not defined CUDA_HOME (
  echo [ERROR] CUDA_HOME not set and no CUDA Toolkit was found under
  echo         "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\".
  echo         Install CUDA Toolkit and re-run, or pass --cuda "PATH".
  exit /b 1
)

if not exist "%CUDA_HOME%\bin\nvcc.exe" (
  echo [ERROR] nvcc not found at: %CUDA_HOME%\bin\nvcc.exe
  exit /b 1
)

set "PATH=%CUDA_HOME%\bin;%PATH%"
echo [INFO] CUDA_HOME=%CUDA_HOME%
"%CUDA_HOME%\bin\nvcc.exe" --version

rem ----- Python build deps -----
echo [INFO] Ensuring build dependencies...
where uv >nul 2>&1
if errorlevel 1 (
  echo [WARN] uv not found; falling back to "%PY_EXE% -m pip".
  "%PY_EXE%" -m pip install -U setuptools wheel ninja packaging build
) else (
  echo [INFO] Using: uv pip install --python "%PY_EXE%"
  uv pip install --python "%PY_EXE%" -U setuptools wheel ninja packaging build
)
if errorlevel 1 (
  echo [ERROR] Failed to install Python build dependencies.
  exit /b 1
)

rem ----- Clean optional / stale ABI -----
set "PY_ABI_TAG="
"%PY_EXE%" -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}{getattr(sys, \"abiflags\", \"\")}')" > "%TEMP%\sageattn_abi.txt" 2>nul
if exist "%TEMP%\sageattn_abi.txt" (
  set /p PY_ABI_TAG=<"%TEMP%\sageattn_abi.txt"
  del "%TEMP%\sageattn_abi.txt" >nul 2>&1
)
set "STALE_ABI=0"
if exist build if defined PY_ABI_TAG (
  dir /b /ad build\lib.win-amd64-cpython-* 2>nul | findstr /I /V "cpython-%PY_ABI_TAG%" >nul 2>&1
  if not errorlevel 1 set "STALE_ABI=1"
  dir /b /ad build\temp.win-amd64-cpython-* 2>nul | findstr /I /V "cpython-%PY_ABI_TAG%" >nul 2>&1
  if not errorlevel 1 set "STALE_ABI=1"
)
if "%DO_CLEAN%"=="1" set "STALE_ABI=1"
if "%STALE_ABI%"=="1" (
  echo [INFO] Cleaning build\ dist\ and egg-info ^(clean/ABI switch^)...
  if exist build rmdir /s /q build
  if exist dist rmdir /s /q dist
  for /d %%D in (*.egg-info) do rmdir /s /q "%%D"
)

rem ----- Build env -----
set "DISTUTILS_USE_SDK=1"
set "MAX_JOBS=%MAX_JOBS%"
set "EXT_PARALLEL=%MAX_JOBS%"
set "CMAKE_BUILD_PARALLEL_LEVEL=%MAX_JOBS%"
if defined ARCH_LIST_OVERRIDE (
  set "TORCH_CUDA_ARCH_LIST=%ARCH_LIST_OVERRIDE%"
  echo [INFO] TORCH_CUDA_ARCH_LIST=%TORCH_CUDA_ARCH_LIST%
) else (
  rem Let setup.py detect from local GPU(s).
  set "TORCH_CUDA_ARCH_LIST="
)

echo.
echo [INFO] Building wheel (this can take a long time)...
echo        Log file: build.log
echo.

"%PY_EXE%" -m build --wheel --no-isolation > build.log 2>&1
if errorlevel 1 (
  echo [ERROR] Build failed. Last 80 lines of build.log:
  echo ------------------------------------------------------------
  powershell -NoProfile -Command "Get-Content -Path 'build.log' -Tail 80"
  echo ------------------------------------------------------------
  exit /b 1
)

rem Scan log for remaining process issues (not just final success).
powershell -NoProfile -Command ^
  "$log = Get-Content -Path 'build.log' -Raw -ErrorAction SilentlyContinue; if (-not $log) { exit 0 };" ^
  "$hard = [regex]::Matches($log, '(?im)^(error:|nvcc fatal|fatal error|FAILED:|undefined reference|LNK[0-9]{4}|error C[0-9]{4})');" ^
  "$warn = [regex]::Matches($log, '(?im)(warning (D9025|#221|#68)\b|cl:.*warning D9025)');" ^
  "if ($hard.Count -gt 0) { Write-Host ('[ERROR] Hard build issues in log: ' + $hard.Count); $hard | Select-Object -First 10 | ForEach-Object { Write-Host $_.Value }; exit 2 };" ^
  "if ($warn.Count -gt 0) { Write-Host ('[WARN] Residual compile warnings of interest: ' + $warn.Count); $warn | Select-Object -First 10 | ForEach-Object { Write-Host $_.Value }; exit 0 };" ^
  "Write-Host '[OK] No hard errors; key warning classes (D9025/#221/#68) not found in build.log'"
if errorlevel 2 (
  echo [ERROR] Build reported success but log still has hard errors.
  exit /b 1
)

echo.
echo [OK] Build succeeded. Wheels in dist\:
dir /b dist\*.whl 2>nul
echo.
echo Install example:
where uv >nul 2>&1
if errorlevel 1 (
  echo   "%PY_EXE%" -m pip install --force-reinstall --no-deps dist\sageattention-*.whl
) else (
  echo   uv pip install --python "%PY_EXE%" --force-reinstall --no-deps dist\sageattention-*.whl
)
echo.
echo Quick smoke test:
echo   "%PY_EXE%" -c "import torch; from sageattention import sageattn; q=torch.randn(1,8,128,64,device='cuda',dtype=torch.float16); print(sageattn(q,q,q).shape)"
echo.
exit /b 0
