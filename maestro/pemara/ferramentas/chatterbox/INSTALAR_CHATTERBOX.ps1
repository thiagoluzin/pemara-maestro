param(
    [string]$InstallRoot = "",
    [string]$ChatterboxRevision = "5de7a54aa4e5e2baadb0182dde554908b48b85c2"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$runtimeRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$workspaceRoot = [System.IO.Path]::GetFullPath((Join-Path $runtimeRoot "..\.."))
$expectedRoot = [System.IO.Path]::GetFullPath(
    (Join-Path $workspaceRoot "ferramentas\chatterbox")
)
if ($runtimeRoot -ne $expectedRoot) {
    throw "O instalador precisa permanecer em $expectedRoot"
}

if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $installRoot = $expectedRoot
} else {
    $installRoot = [System.IO.Path]::GetFullPath($InstallRoot)
}
$installDriveRoot = [System.IO.Path]::GetPathRoot($installRoot)
if ($installRoot.TrimEnd("\") -eq $installDriveRoot.TrimEnd("\")) {
    throw "A raiz de um disco nao pode ser usada como pasta de instalacao."
}
$drive = Get-PSDrive -Name ($installDriveRoot.TrimEnd(":\"))
$minimumFreeBytes = 15GB
if ($drive.Free -lt $minimumFreeBytes) {
    $freeGb = [Math]::Round($drive.Free / 1GB, 1)
    throw "Espaco insuficiente em ${installDriveRoot}: $freeGb GB livres. Sao exigidos 15 GB para instalar com seguranca."
}
New-Item -ItemType Directory -Force -Path $installRoot | Out-Null

# Mantem ambiente, temporarios e todos os caches neurais no mesmo runtime em E:.
# Isso evita que Hugging Face, Torch ou builders depositem modelos privados em C:.
$cacheRoot = Join-Path $installRoot "model-cache"
$tempRoot = Join-Path $installRoot "tmp"
$hfHome = Join-Path $cacheRoot "huggingface"
$torchHome = Join-Path $cacheRoot "torch"
foreach ($directory in @($cacheRoot, $tempRoot, $hfHome, $torchHome)) {
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
}
$env:HF_HOME = $hfHome
$env:HF_HUB_CACHE = Join-Path $hfHome "hub"
$env:HUGGINGFACE_HUB_CACHE = Join-Path $hfHome "hub"
$env:TORCH_HOME = $torchHome
$env:XDG_CACHE_HOME = $cacheRoot
$env:TEMP = $tempRoot
$env:TMP = $tempRoot

$python = "C:\Program Files\Python311\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    $command = Get-Command python -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "Python 3.11 nao foi encontrado."
    }
    $python = $command.Source
}

$version = & $python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0 -or $version.Trim() -ne "3.11") {
    throw "Chatterbox requer o Python 3.11 isolado; encontrado: $version"
}

$hasBaseCuda = $false
& $python -c "import torch, torchaudio; raise SystemExit(0 if torch.cuda.is_available() else 1)" 2>$null
if ($LASTEXITCODE -eq 0) {
    $hasBaseCuda = $true
}

$venv = Join-Path $installRoot ".venv"
$venvPython = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    $venvArgs = @("-m", "venv")
    if ($hasBaseCuda) {
        $venvArgs += "--system-site-packages"
    }
    $venvArgs += $venv
    & $python @venvArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao criar o ambiente isolado."
    }
}

& $venvPython -m pip install --disable-pip-version-check --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao atualizar o pip do ambiente isolado."
}

& $venvPython -m pip install --disable-pip-version-check --no-cache-dir `
    "git+https://github.com/resemble-ai/chatterbox.git@$ChatterboxRevision"
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao instalar a revisao oficial do chatterbox-tts."
}

if ($hasBaseCuda) {
    # O pacote PyPI fixa uma build CPU do Torch 2.6. Nesta estacao a pilha CUDA
    # validada do Maestro ja suporta a RTX 5090; compartilhe-a com o ambiente e
    # remova somente a copia CPU instalada dentro do venv.
    $venvConfig = Join-Path $venv "pyvenv.cfg"
    $configText = [IO.File]::ReadAllText($venvConfig)
    $configText = $configText -replace "include-system-site-packages\s*=\s*false", "include-system-site-packages = true"
    [IO.File]::WriteAllText($venvConfig, $configText, [Text.UTF8Encoding]::new($false))
    $localTorch = Join-Path $venv "Lib\site-packages\torch"
    if (Test-Path -LiteralPath $localTorch -PathType Container) {
        & $venvPython -m pip uninstall -y torch torchaudio
        if ($LASTEXITCODE -ne 0) {
            throw "Falha ao remover a copia CPU duplicada do Torch."
        }
    }
}

& $venvPython -c "from chatterbox.mtl_tts import ChatterboxMultilingualTTS; print('Chatterbox Multilingual pronto')"
if ($LASTEXITCODE -ne 0) {
    throw "O pacote foi instalado, mas a importacao de validacao falhou."
}
if ($hasBaseCuda) {
    & $venvPython -c "import torch; raise SystemExit(0 if torch.cuda.is_available() else 1)"
    if ($LASTEXITCODE -ne 0) {
        throw "O Chatterbox foi instalado, mas o ambiente nao herdou a CUDA validada."
    }
}

Write-Host "Chatterbox instalado em $venv."
Write-Host "Cache neural configurado em $cacheRoot."
Write-Host "O Studio detecta automaticamente este ambiente local."
