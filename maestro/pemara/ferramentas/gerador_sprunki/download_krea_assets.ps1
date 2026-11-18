param(
    [string]$Python = "python",
    [string]$ComfyModelsDir = "E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models",
    [switch]$FullTrainingModel,
    [switch]$RequireFullTrainingModel
)

$ErrorActionPreference = "Stop"

$UnetDir = Join-Path $ComfyModelsDir "unet"
New-Item -ItemType Directory -Force -Path $UnetDir | Out-Null

function Invoke-HfDownload {
    param(
        [string]$Repo,
        [string]$File,
        [string]$LocalDir
    )

    $args = @(
        "-m", "huggingface_hub.commands.huggingface_cli",
        "download", $Repo,
        $File,
        "--local-dir", $LocalDir,
        "--local-dir-use-symlinks", "False"
    )

    & $Python @args
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao baixar $Repo/$File. Se o repositorio exigir aceite, defina HF_TOKEN depois de aceitar a licenca no Hugging Face."
    }
}

function Write-HfLoginHelp {
    Write-Host ""
    Write-Host "Modelo completo Krea bloqueado pelo Hugging Face (repo gated)." -ForegroundColor Yellow
    Write-Host "Para liberar:"
    Write-Host "1. Acesse: https://huggingface.co/black-forest-labs/FLUX.1-Krea-dev"
    Write-Host "2. Aceite os termos/licenca do modelo."
    Write-Host "3. Gere um token em: https://huggingface.co/settings/tokens"
    Write-Host "4. No PowerShell, rode uma das opcoes:"
    Write-Host '   huggingface-cli login'
    Write-Host '   ou: $env:HF_TOKEN="hf_SEU_TOKEN_AQUI"'
    Write-Host "5. Depois rode novamente com -FullTrainingModel."
    Write-Host ""
}

try {
    & $Python -c "import huggingface_hub" 2>$null
    if ($LASTEXITCODE -ne 0) {
        & $Python -m pip install -U huggingface_hub
    }

    $fp8Target = Join-Path $UnetDir "flux1-krea-dev_fp8_scaled.safetensors"
    if (-not (Test-Path -LiteralPath $fp8Target)) {
        Invoke-HfDownload `
            -Repo "Comfy-Org/FLUX.1-Krea-dev_ComfyUI" `
            -File "split_files/diffusion_models/flux1-krea-dev_fp8_scaled.safetensors" `
            -LocalDir $UnetDir

        $downloaded = Join-Path $UnetDir "split_files\diffusion_models\flux1-krea-dev_fp8_scaled.safetensors"
        if (Test-Path -LiteralPath $downloaded) {
            Move-Item -LiteralPath $downloaded -Destination $fp8Target -Force
        }
    }

    if ($FullTrainingModel) {
        $fullTarget = Join-Path $UnetDir "flux1-krea-dev.safetensors"
        if (-not (Test-Path -LiteralPath $fullTarget)) {
            try {
                Invoke-HfDownload `
                    -Repo "black-forest-labs/FLUX.1-Krea-dev" `
                    -File "flux1-krea-dev.safetensors" `
                    -LocalDir $UnetDir
            } catch {
                Write-HfLoginHelp
                if ($RequireFullTrainingModel) {
                    throw $_
                }
                Write-Warning "FP8 de geracao continua valido. Treino Krea completo foi pulado por falta de acesso autenticado."
            }
        }
    }

    Write-Host "Krea assets prontos em $UnetDir"
} catch {
    Write-Error $_
    exit 1
}
