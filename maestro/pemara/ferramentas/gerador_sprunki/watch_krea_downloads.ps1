param(
    [string]$DownloadsDir = "$env:USERPROFILE\Downloads",
    [string]$ComfyModelsDir = "E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models",
    [int]$TimeoutMinutes = 180,
    [int]$StableChecks = 3,
    [int]$StableIntervalSeconds = 20,
    [switch]$RunCompareAfterMove,
    [switch]$InstallKreaWeeklyTraining
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $Root "logs"
$LogFile = Join-Path $LogDir "krea_download_watcher.log"
$UnetDir = Join-Path $ComfyModelsDir "unet"
$ComfyHealth = "http://127.0.0.1:8188/system_stats"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
New-Item -ItemType Directory -Force -Path $UnetDir | Out-Null

$Targets = @{
    "flux1-krea-dev_fp8_scaled.safetensors" = Join-Path $UnetDir "flux1-krea-dev_fp8_scaled.safetensors"
    "flux1-krea-dev.safetensors" = Join-Path $UnetDir "flux1-krea-dev.safetensors"
}

function Write-Log {
    param([string]$Message)
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$stamp] $Message"
    Add-Content -Path $LogFile -Value $line
    Write-Host $line
}

function Test-ComfyHealth {
    try {
        $response = Invoke-WebRequest -Uri $ComfyHealth -UseBasicParsing -TimeoutSec 10
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300)
    } catch {
        return $false
    }
}

function Get-CandidateFile {
    param([string]$FileName)

    $exact = Join-Path $DownloadsDir $FileName
    if (Test-Path -LiteralPath $exact) {
        return Get-Item -LiteralPath $exact
    }

    $stem = [System.IO.Path]::GetFileNameWithoutExtension($FileName)
    $matches = Get-ChildItem -LiteralPath $DownloadsDir -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "$stem*.safetensors" -and $_.Extension -eq ".safetensors" } |
        Sort-Object LastWriteTime -Descending

    return $matches | Select-Object -First 1
}

function Test-DownloadStillActive {
    param([string]$BaseName)

    $stem = [System.IO.Path]::GetFileNameWithoutExtension($BaseName)
    $active = Get-ChildItem -LiteralPath $DownloadsDir -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -like "$stem*" -and
            ($_.Name.EndsWith(".crdownload") -or $_.Name.EndsWith(".part") -or $_.Name.EndsWith(".tmp"))
        }

    return [bool]$active
}

function Wait-FileStable {
    param([System.IO.FileInfo]$File)

    $stable = 0
    $lastSize = -1

    while ($stable -lt $StableChecks) {
        if (-not (Test-Path -LiteralPath $File.FullName)) {
            return $false
        }

        $current = Get-Item -LiteralPath $File.FullName
        if ($current.Length -eq $lastSize -and $current.Length -gt 0) {
            $stable += 1
        } else {
            $stable = 0
            $lastSize = $current.Length
        }

        Start-Sleep -Seconds $StableIntervalSeconds
    }

    return $true
}

function Move-Target {
    param(
        [string]$FileName,
        [string]$Destination
    )

    if (Test-Path -LiteralPath $Destination) {
        $size = [math]::Round((Get-Item -LiteralPath $Destination).Length / 1GB, 2)
        Write-Log "Ja existe no destino: $Destination (${size}GB)"
        $duplicate = Get-CandidateFile -FileName $FileName
        if ($duplicate -and -not (Test-DownloadStillActive -BaseName $FileName)) {
            $dupSize = [math]::Round($duplicate.Length / 1GB, 2)
            Write-Log "Removendo duplicado em Downloads: $($duplicate.FullName) (${dupSize}GB)"
            Remove-Item -LiteralPath $duplicate.FullName -Force
        }
        return $true
    }

    $candidate = Get-CandidateFile -FileName $FileName
    if (-not $candidate) {
        return $false
    }

    if (Test-DownloadStillActive -BaseName $FileName) {
        Write-Log "Download ainda ativo para $FileName"
        return $false
    }

    Write-Log "Arquivo encontrado: $($candidate.FullName). Aguardando estabilidade..."
    if (-not (Wait-FileStable -File $candidate)) {
        Write-Log "Arquivo desapareceu antes de estabilizar: $($candidate.FullName)"
        return $false
    }

    $size = [math]::Round((Get-Item -LiteralPath $candidate.FullName).Length / 1GB, 2)
    Write-Log "Movendo $($candidate.Name) (${size}GB) para $Destination"
    Move-Item -LiteralPath $candidate.FullName -Destination $Destination -Force
    return $true
}

$deadline = (Get-Date).AddMinutes($TimeoutMinutes)
Write-Log "Watcher iniciado. Downloads=$DownloadsDir Destino=$UnetDir Timeout=${TimeoutMinutes}min"

while ((Get-Date) -lt $deadline) {
    $movedAny = $false
    foreach ($entry in $Targets.GetEnumerator()) {
        if (Move-Target -FileName $entry.Key -Destination $entry.Value) {
            $movedAny = $true
        }
    }

    $fp8Ok = Test-Path -LiteralPath $Targets["flux1-krea-dev_fp8_scaled.safetensors"]
    $fullOk = Test-Path -LiteralPath $Targets["flux1-krea-dev.safetensors"]

    if ($fp8Ok -and $fullOk) {
        Write-Log "Krea FP8 e modelo completo estao no lugar."
        break
    }

    if ($movedAny) {
        Write-Log "Estado parcial: FP8=$fp8Ok Full=$fullOk"
    }

    Start-Sleep -Seconds 60
}

$fp8Ok = Test-Path -LiteralPath $Targets["flux1-krea-dev_fp8_scaled.safetensors"]
$fullOk = Test-Path -LiteralPath $Targets["flux1-krea-dev.safetensors"]
Write-Log "Estado final: FP8=$fp8Ok Full=$fullOk"

if (-not (Test-ComfyHealth)) {
    Write-Log "ComfyUI nao respondeu. Chamando watchdog/start."
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root "watchdog_comfyui.ps1") -Once | Out-Null
}

if (Test-ComfyHealth) {
    Write-Log "ComfyUI saudavel em $ComfyHealth"
} else {
    Write-Log "ComfyUI ainda indisponivel depois do watchdog."
}

if ($RunCompareAfterMove -and $fp8Ok -and (Test-ComfyHealth)) {
    Write-Log "Rodando comparacao A/B curta com Krea FP8."
    & python (Join-Path $Root "compare_flux_models.py") --limit 1 --timeout 900
    Write-Log "Comparacao A/B finalizada com code=$LASTEXITCODE"
}

if ($InstallKreaWeeklyTraining -and $fullOk) {
    Write-Log "Instalando tarefa semanal de treino Krea experimental."
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root "install_weekly_krea_lora_task.ps1")
    Write-Log "Instalador de treino Krea finalizado com code=$LASTEXITCODE"
}

Write-Log "Watcher finalizado."
