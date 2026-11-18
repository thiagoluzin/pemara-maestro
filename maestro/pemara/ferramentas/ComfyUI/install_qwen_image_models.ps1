param(
    [switch]$Parallel
)

$ErrorActionPreference = "Stop"

$ComfyRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ModelsDir = Join-Path $ComfyRoot "models"
$LogDir = Join-Path (Split-Path -Parent (Split-Path -Parent $ComfyRoot)) "dados\logs"
$LogFile = Join-Path $LogDir "qwen_image_install.log"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Log($Message) {
    "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message" | Tee-Object -FilePath $LogFile -Append
}

function Download-Model($Label, $Url, $Dest, $MinGB) {
    $destPath = [System.IO.Path]::GetFullPath($Dest)
    $destDir = Split-Path -Parent $destPath
    $tmpPath = "$destPath.download"
    $minBytes = [int64]($MinGB * 1GB)
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null

    if (Test-Path -LiteralPath $destPath) {
        $existing = Get-Item -LiteralPath $destPath
        $gb = [Math]::Round($existing.Length / 1GB, 2)
        if ($existing.Length -ge $minBytes) {
            Log "[OK] $Label ja existe: $destPath ($gb GB)"
            return
        }
        Log "[WARN] $Label existe pequeno demais ($gb GB). Vou baixar novamente."
        Move-Item -LiteralPath $destPath -Destination "$destPath.invalid_$(Get-Date -Format 'yyyyMMdd_HHmmss')" -Force
    }

    Log "[DOWNLOAD] $Label"
    Log "URL: $Url"
    Log "Destino temporario: $tmpPath"

    $args = @(
        "--silent",
        "--show-error",
        "--fail",
        "--location",
        "--continue-at", "-",
        "--retry", "30",
        "--retry-delay", "10",
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
        $got = if (Test-Path -LiteralPath $tmpPath) { [Math]::Round((Get-Item -LiteralPath $tmpPath).Length / 1GB, 2) } else { 0 }
        throw "download invalido ou pequeno para $Label ($got GB, minimo esperado $MinGB GB)"
    }

    Move-Item -LiteralPath $tmpPath -Destination $destPath -Force
    $finalGb = [Math]::Round((Get-Item -LiteralPath $destPath).Length / 1GB, 2)
    Log "[OK] $Label salvo: $destPath ($finalGb GB)"
}

function Start-DownloadJob($Item) {
    Start-Job -Name $Item.Label -ArgumentList $Item.Label, $Item.Url, $Item.Dest, $Item.MinGB, $LogFile -ScriptBlock {
        param($Label, $Url, $Dest, $MinGB, $LogFile)
        $ErrorActionPreference = "Stop"

        function Write-JobLog($Message) {
            "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message" | Add-Content -Path $LogFile
        }

        $destPath = [System.IO.Path]::GetFullPath($Dest)
        $destDir = Split-Path -Parent $destPath
        $tmpPath = "$destPath.download"
        $minBytes = [int64]($MinGB * 1GB)
        New-Item -ItemType Directory -Force -Path $destDir | Out-Null

        if (Test-Path -LiteralPath $destPath) {
            $existing = Get-Item -LiteralPath $destPath
            $gb = [Math]::Round($existing.Length / 1GB, 2)
            if ($existing.Length -ge $minBytes) {
                Write-JobLog "[OK] $Label ja existe: $destPath ($gb GB)"
                return
            }
            Write-JobLog "[WARN] $Label existe pequeno demais ($gb GB). Vou baixar novamente."
            Move-Item -LiteralPath $destPath -Destination "$destPath.invalid_$(Get-Date -Format 'yyyyMMdd_HHmmss')" -Force
        }

        Write-JobLog "[DOWNLOAD] $Label"
        Write-JobLog "URL: $Url"
        Write-JobLog "Destino temporario: $tmpPath"

        $args = @(
            "--silent",
            "--show-error",
            "--fail",
            "--location",
            "--continue-at", "-",
            "--retry", "30",
            "--retry-delay", "10",
            "--connect-timeout", "60",
            "--speed-time", "120",
            "--speed-limit", "1024",
            "--output", $tmpPath
        )

        if ($env:HF_TOKEN) {
            $args += @("--header", "Authorization: Bearer $env:HF_TOKEN")
        }

        $args += $Url
        & curl.exe @args 2>&1 | ForEach-Object { Add-Content -Path $LogFile -Value $_ }
        if ($LASTEXITCODE -ne 0) {
            throw "curl falhou com exit code $LASTEXITCODE para $Label"
        }

        if (-not (Test-Path -LiteralPath $tmpPath) -or ((Get-Item -LiteralPath $tmpPath).Length -lt $minBytes)) {
            $got = if (Test-Path -LiteralPath $tmpPath) { [Math]::Round((Get-Item -LiteralPath $tmpPath).Length / 1GB, 2) } else { 0 }
            throw "download invalido ou pequeno para $Label ($got GB, minimo esperado $MinGB GB)"
        }

        Move-Item -LiteralPath $tmpPath -Destination $destPath -Force
        $finalGb = [Math]::Round((Get-Item -LiteralPath $destPath).Length / 1GB, 2)
        Write-JobLog "[OK] $Label salvo: $destPath ($finalGb GB)"
    }
}

Log "Instalacao Qwen Image iniciada"
Log "ComfyUI: $ComfyRoot"
Log "Models: $ModelsDir"
Log "Metodo: curl.exe com resume"

$items = @(
    @{
        Label = "Qwen Image 2512 FP8"
        Url = "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_2512_fp8_e4m3fn.safetensors"
        Dest = Join-Path $ModelsDir "diffusion_models\qwen_image_2512_fp8_e4m3fn.safetensors"
        MinGB = 18
    },
    @{
        Label = "Qwen text encoder FP8"
        Url = "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors"
        Dest = Join-Path $ModelsDir "text_encoders\qwen_2.5_vl_7b_fp8_scaled.safetensors"
        MinGB = 8
    },
    @{
        Label = "Qwen Image VAE"
        Url = "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors"
        Dest = Join-Path $ModelsDir "vae\qwen_image_vae.safetensors"
        MinGB = 0.2
    },
    @{
        Label = "Qwen Image 2512 Lightning 4 steps"
        Url = "https://huggingface.co/lightx2v/Qwen-Image-2512-Lightning/resolve/main/Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors"
        Dest = Join-Path $ModelsDir "loras\Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors"
        MinGB = 1.4
    },
    @{
        Label = "Qwen Image Edit 2511 FP8 mixed"
        Url = "https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors"
        Dest = Join-Path $ModelsDir "diffusion_models\qwen_image_edit_2511_fp8mixed.safetensors"
        MinGB = 18
    },
    @{
        Label = "Qwen tokenizer merges"
        Url = "https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct/resolve/main/merges.txt"
        Dest = Join-Path $ComfyRoot "comfy\text_encoders\qwen25_tokenizer\merges.txt"
        MinGB = 0.001
    },
    @{
        Label = "Qwen tokenizer json"
        Url = "https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct/resolve/main/tokenizer.json"
        Dest = Join-Path $ComfyRoot "comfy\text_encoders\qwen25_tokenizer\tokenizer.json"
        MinGB = 0.006
    }
)

if ($Parallel) {
    Log "Modo paralelo ativado"
    $jobs = foreach ($item in $items) {
        Start-DownloadJob -Item $item
    }
    $jobs | Wait-Job | Out-Null
    $failed = $jobs | Where-Object { $_.State -ne "Completed" }
    $jobs | Receive-Job
    $jobs | Remove-Job
    if ($failed) {
        throw "Uma ou mais transferencias falharam: $($failed.Name -join ', ')"
    }
} else {
    foreach ($item in $items) {
        Download-Model -Label $item.Label -Url $item.Url -Dest $item.Dest -MinGB $item.MinGB
    }
}

Log "Instalacao Qwen Image finalizada"
