param(
    [switch]$SkipCustomNodes,
    [switch]$SkipModels,
    [switch]$Parallel
)

$ErrorActionPreference = "Stop"

$ComfyRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ModelsDir = Join-Path $ComfyRoot "models"
$CustomNodesDir = Join-Path $ComfyRoot "custom_nodes"
$LogDir = Join-Path (Split-Path -Parent (Split-Path -Parent $ComfyRoot)) "dados\logs"
$LogFile = Join-Path $LogDir "pemara_image_max_stack_install.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
New-Item -ItemType Directory -Force -Path $CustomNodesDir | Out-Null

function Log($Message) {
    "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message" | Tee-Object -FilePath $LogFile -Append
}

function Download-File($Label, $Url, $Dest, $MinMB) {
    $destPath = [System.IO.Path]::GetFullPath($Dest)
    $destDir = Split-Path -Parent $destPath
    $tmpPath = "$destPath.download"
    $minBytes = [int64]($MinMB * 1MB)
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null

    if (Test-Path -LiteralPath $destPath) {
        $existing = Get-Item -LiteralPath $destPath
        $mb = [Math]::Round($existing.Length / 1MB, 1)
        if ($existing.Length -ge $minBytes) {
            Log "[OK] $Label ja existe: $destPath ($mb MB)"
            return
        }
        $invalid = "$destPath.invalid_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        Log "[WARN] $Label existe pequeno demais ($mb MB). Movendo para $invalid"
        Move-Item -LiteralPath $destPath -Destination $invalid -Force
    }

    Log "[DOWNLOAD] $Label"
    Log "URL: $Url"
    Log "Destino: $destPath"
    $args = @(
        "--silent",
        "--show-error",
        "--fail",
        "--location",
        "--continue-at", "-",
        "--retry", "30",
        "--retry-delay", "8",
        "--connect-timeout", "60",
        "--speed-time", "120",
        "--speed-limit", "1024",
        "--output", $tmpPath
    )
    if ($env:HF_TOKEN) {
        $args += @("--header", "Authorization: Bearer $env:HF_TOKEN")
    }
    $args += $Url
    & curl.exe @args 2>&1 | Tee-Object -FilePath $LogFile -Append
    if ($LASTEXITCODE -ne 0) {
        throw "curl falhou com exit code $LASTEXITCODE para $Label"
    }
    if (-not (Test-Path -LiteralPath $tmpPath) -or ((Get-Item -LiteralPath $tmpPath).Length -lt $minBytes)) {
        $got = if (Test-Path -LiteralPath $tmpPath) { [Math]::Round((Get-Item -LiteralPath $tmpPath).Length / 1MB, 1) } else { 0 }
        throw "download invalido para $Label ($got MB, minimo esperado $MinMB MB)"
    }
    Move-Item -LiteralPath $tmpPath -Destination $destPath -Force
    $finalMb = [Math]::Round((Get-Item -LiteralPath $destPath).Length / 1MB, 1)
    Log "[OK] $Label salvo: $destPath ($finalMb MB)"
}

function Start-DownloadJob($Item) {
    Start-Job -Name $Item.Label -ArgumentList $Item.Label, $Item.Url, $Item.Dest, $Item.MinMB, $LogFile -ScriptBlock {
        param($Label, $Url, $Dest, $MinMB, $LogFile)
        $ErrorActionPreference = "Stop"
        function JLog($Message) {
            "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message" | Add-Content -Path $LogFile
        }
        $destPath = [System.IO.Path]::GetFullPath($Dest)
        $destDir = Split-Path -Parent $destPath
        $tmpPath = "$destPath.download"
        $minBytes = [int64]($MinMB * 1MB)
        New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        if (Test-Path -LiteralPath $destPath) {
            $existing = Get-Item -LiteralPath $destPath
            if ($existing.Length -ge $minBytes) {
                JLog "[OK] $Label ja existe: $destPath"
                return
            }
            Move-Item -LiteralPath $destPath -Destination "$destPath.invalid_$(Get-Date -Format 'yyyyMMdd_HHmmss')" -Force
        }
        JLog "[DOWNLOAD] $Label"
        $args = @(
            "--silent", "--show-error", "--fail", "--location",
            "--continue-at", "-", "--retry", "30", "--retry-delay", "8",
            "--connect-timeout", "60", "--speed-time", "120", "--speed-limit", "1024",
            "--output", $tmpPath
        )
        if ($env:HF_TOKEN) {
            $args += @("--header", "Authorization: Bearer $env:HF_TOKEN")
        }
        $args += $Url
        & curl.exe @args 2>&1 | ForEach-Object { Add-Content -Path $LogFile -Value $_ }
        if ($LASTEXITCODE -ne 0) { throw "curl falhou com exit code $LASTEXITCODE para $Label" }
        if (-not (Test-Path -LiteralPath $tmpPath) -or ((Get-Item -LiteralPath $tmpPath).Length -lt $minBytes)) {
            throw "download invalido para $Label"
        }
        Move-Item -LiteralPath $tmpPath -Destination $destPath -Force
        JLog "[OK] $Label salvo: $destPath"
    }
}

function Ensure-GitRepo($Name, $Url) {
    $dest = Join-Path $CustomNodesDir $Name
    if (Test-Path -LiteralPath (Join-Path $dest ".git")) {
        Log "[UPDATE] $Name"
        $oldEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            git -C $dest pull --ff-only 2>&1 | Tee-Object -FilePath $LogFile -Append
            if ($LASTEXITCODE -ne 0) {
                Log "[WARN] Nao consegui atualizar $Name. Mantendo copia existente."
            }
        } finally {
            $ErrorActionPreference = $oldEap
        }
        return
    }
    if (Test-Path -LiteralPath $dest) {
        Log "[OK] $Name ja existe sem .git: $dest"
        return
    }
    Log "[CLONE] $Name -> $dest"
    $oldEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        git clone --depth 1 $Url $dest 2>&1 | Tee-Object -FilePath $LogFile -Append
        if ($LASTEXITCODE -ne 0) {
            throw "git clone falhou para $Name"
        }
    } finally {
        $ErrorActionPreference = $oldEap
    }
}

Log "Instalacao Pemara Image Max iniciada"
Log "ComfyUI: $ComfyRoot"

if (-not $SkipModels) {
    $modelItems = @(
        @{
            Label = "RealESRGAN_x4plus"
            Url = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
            Dest = Join-Path $ModelsDir "upscale_models\RealESRGAN_x4plus.pth"
            MinMB = 60
        },
        @{
            Label = "RealESRNet_x4plus"
            Url = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.1/RealESRNet_x4plus.pth"
            Dest = Join-Path $ModelsDir "upscale_models\RealESRNet_x4plus.pth"
            MinMB = 60
        },
        @{
            Label = "4x-UltraSharp"
            Url = "https://huggingface.co/lokCX/4x-Ultrasharp/resolve/main/4x-UltraSharp.pth"
            Dest = Join-Path $ModelsDir "upscale_models\4x-UltraSharp.pth"
            MinMB = 60
        },
        @{
            Label = "4x_NMKD-Superscale-SP"
            Url = "https://huggingface.co/uwg/upscaler/resolve/main/ESRGAN/4x_NMKD-Superscale-SP_178000_G.pth"
            Dest = Join-Path $ModelsDir "upscale_models\4x_NMKD-Superscale-SP_178000_G.pth"
            MinMB = 60
        },
        @{
            Label = "sigclip vision for Flux Redux"
            Url = "https://huggingface.co/Comfy-Org/sigclip_vision_384/resolve/main/sigclip_vision_patch14_384.safetensors"
            Dest = Join-Path $ModelsDir "clip_vision\sigclip_vision_patch14_384.safetensors"
            MinMB = 600
        },
        @{
            Label = "FLUX.1 Redux dev"
            Url = "https://huggingface.co/black-forest-labs/FLUX.1-Redux-dev/resolve/main/flux1-redux-dev.safetensors"
            Dest = Join-Path $ModelsDir "style_models\flux1-redux-dev.safetensors"
            MinMB = 650
        },
        @{
            Label = "XLabs Flux ControlNet Canny v3"
            Url = "https://huggingface.co/XLabs-AI/flux-controlnet-canny-v3/resolve/main/flux-canny-controlnet-v3.safetensors"
            Dest = Join-Path $ModelsDir "controlnet\flux-canny-controlnet-v3.safetensors"
            MinMB = 1200
        },
        @{
            Label = "XLabs Flux ControlNet Depth v3"
            Url = "https://huggingface.co/XLabs-AI/flux-controlnet-depth-v3/resolve/main/flux-depth-controlnet-v3.safetensors"
            Dest = Join-Path $ModelsDir "controlnet\flux-depth-controlnet-v3.safetensors"
            MinMB = 1200
        }
    )

    if ($Parallel) {
        $jobs = foreach ($item in $modelItems) { Start-DownloadJob -Item $item }
        $jobs | Wait-Job | Out-Null
        $failed = $jobs | Where-Object { $_.State -ne "Completed" }
        $jobs | Receive-Job
        $jobs | Remove-Job
        if ($failed) {
            throw "Downloads falharam: $($failed.Name -join ', ')"
        }
    } else {
        foreach ($item in $modelItems) {
            try {
                Download-File -Label $item.Label -Url $item.Url -Dest $item.Dest -MinMB $item.MinMB
            } catch {
                Log "[WARN] $($item.Label) nao instalado: $($_.Exception.Message)"
            }
        }
    }
}

if (-not $SkipCustomNodes) {
    Ensure-GitRepo -Name "ComfyUI_essentials" -Url "https://github.com/comfyorg/comfyui-essentials.git"
    Ensure-GitRepo -Name "comfyui_controlnet_aux" -Url "https://github.com/Fannovel16/comfyui_controlnet_aux.git"
    Ensure-GitRepo -Name "comfyui-ipadapter" -Url "https://github.com/comfyorg/comfyui-ipadapter.git"
    Ensure-GitRepo -Name "x-flux-comfyui" -Url "https://github.com/XLabs-AI/x-flux-comfyui.git"

    $requirements = @(
        (Join-Path $CustomNodesDir "ComfyUI_essentials\requirements.txt"),
        (Join-Path $CustomNodesDir "comfyui_controlnet_aux\requirements.txt"),
        (Join-Path $CustomNodesDir "comfyui-ipadapter\requirements.txt"),
        (Join-Path $CustomNodesDir "x-flux-comfyui\requirements.txt")
    )
    foreach ($req in $requirements) {
        if (Test-Path -LiteralPath $req) {
            Log "[PIP] $req"
            $oldEap = $ErrorActionPreference
            $ErrorActionPreference = "Continue"
            try {
                python -m pip install --user -r $req 2>&1 | Tee-Object -FilePath $LogFile -Append
                if ($LASTEXITCODE -ne 0) {
                    Log "[WARN] pip retornou exit code $LASTEXITCODE em $req"
                }
            } finally {
                $ErrorActionPreference = $oldEap
            }
        }
    }
}

Log "Instalacao Pemara Image Max finalizada"
Log "Reinicie o ComfyUI depois que nao houver treino/geracao rodando para carregar novos custom nodes."
