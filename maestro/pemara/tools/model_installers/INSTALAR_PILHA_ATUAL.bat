@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "PEMARA_NO_PAUSE=1"
rem Instalar esta pilha nao autoriza render, novos sons ou reativar motores removidos.
for %%B in (01_INSTALAR_H3.bat 02_INSTALAR_QWEN_H3.bat 06_INSTALAR_AVALIADOR_GEMMA4.bat 04_INSTALAR_FOLEY_XXL.bat 05_INSTALAR_RIFE_425_ATUAL.bat) do (
    call "%~dp0%%B" %*
    if errorlevel 1 exit /b 1
)
exit /b 0
