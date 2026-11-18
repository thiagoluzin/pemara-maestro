@echo off
REM run_evolution.bat - Script de execução rápida do Agente de Evolução Sprunki

echo ============================================================
echo  AGENTE DE EVOLUÇÃO SPRUNKI - INICIANDO
echo ============================================================
echo.

REM Verifica se Python está disponível
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python não encontrado!
    echo Instale Python 3.10+ de https://python.org
    pause
    exit /b 1
)

echo Python detectado. Inicializando...
echo.

REM Opções de execução
echo Escolha o modo de execução:
echo.
echo 1. Modo DRY RUN (só gera e avalia, não treina)
echo 2. Modo AUTOMATICO (gera, avalia e treina)
echo 3. Modo PERSONALIZADO
echo.
set /p MODE="Digite sua escolha (1/2/3): "

if "%MODE%"=="1" (
    echo.
    echo Iniciando modo DRY RUN...
    python run_evolution.py --dry-run --target-score 85 --max-epochs 10
) else if "%MODE%"=="2" (
    echo.
    echo Iniciando modo AUTOMATICO...
    echo Certifique-se que Kohya SS está configurado!
    echo.
    set /p CONFIRM="Continuar? (S/N): "
    if /i not "%CONFIRM%"=="S" (
        echo Cancelado.
        pause
        exit /b 0
    )
    python run_evolution.py --target-score 85 --max-epochs 20
) else if "%MODE%"=="3" (
    echo.
    echo Modo Personalizado...
    set /p TARGET="Score alvo (padrao 85): "
    set /p EPOCHS="Maximo de epochs (padrao 20): "
    set /p GEN="Gerações por epoch (padrao 15): "
    
    set TARGET=%TARGET: =%
    set EPOCHS=%EPOCHS: =%
    set GEN=%GEN: =%
    
    if "%TARGET%"=="" set TARGET=85
    if "%EPOCHS%"=="" set EPOCHS=20
    if "%GEN%"=="" set GEN=15
    
    python run_evolution.py --target-score %TARGET% --max-epochs %EPOCHS% --generations %GEN%
) else (
    echo Opção inválida.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  EXECUÇÃO CONCLUÍDA
echo ============================================================
echo.
pause