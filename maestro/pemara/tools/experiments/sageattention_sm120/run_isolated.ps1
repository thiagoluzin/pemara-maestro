$ErrorActionPreference = "Stop"

$experimentRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$workspaceRoot = Resolve-Path (Join-Path $experimentRoot "..\..\..")
$sourceRoot = Resolve-Path (Join-Path $workspaceRoot "tools\experiments\SageAttention-official")
$venvRoot = Join-Path $experimentRoot ".venv"
$venvPython = Join-Path $venvRoot "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    py -3.11 -m venv --system-site-packages $venvRoot
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao criar o ambiente virtual isolado."
    }
}

$env:CL = (($env:CL + " /Zc:preprocessor").Trim())
$env:MAX_JOBS = "4"
$env:EXT_PARALLEL = "1"
$env:CXX_APPEND_FLAGS = "/std:c++20"
$env:NVCC_APPEND_FLAGS = "-std=c++20"
& $venvPython -m pip install --no-build-isolation $sourceRoot
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao compilar ou instalar SageAttention no ambiente isolado."
}
& $venvPython (Join-Path $experimentRoot "verify_sageattention.py")
if ($LASTEXITCODE -ne 0) {
    throw "O smoke numerico isolado do SageAttention foi reprovado."
}
