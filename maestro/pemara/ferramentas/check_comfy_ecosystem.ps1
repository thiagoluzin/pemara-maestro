param(
    [string]$ComfyRoot = "E:\Pemara\maestro\pemara\ferramentas\ComfyUI",
    [int]$Port = 8188
)

$ErrorActionPreference = "SilentlyContinue"
$HealthUrl = "http://127.0.0.1:$Port/system_stats"
$LoraVideos = Join-Path $ComfyRoot "lora_videos"
$Marketing = "E:\Pemara\marketing_social"
$Sprunki = "E:\Pemara\maestro\pemara\ferramentas\gerador_sprunki"

function Show-Title($text) {
    Write-Host ""
    Write-Host "=== $text ==="
}

Show-Title "ComfyUI Principal"
Write-Host "Root: $ComfyRoot"
try {
    $stats = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 8
    Write-Host "Health: OK $HealthUrl ($($stats.StatusCode))"
    $json = $stats.Content | ConvertFrom-Json
    $argv = @($json.system.argv)
    if ($argv -contains "--listen") {
        $listenIndex = [array]::IndexOf($argv, "--listen")
        if ($listenIndex -ge 0 -and ($listenIndex + 1) -lt $argv.Count) {
            $listenHost = $argv[$listenIndex + 1]
            if ($listenHost -in @("0.0.0.0", "::")) {
                Write-Host "Listen: FALHOU ($listenHost exposto)"
            } else {
                Write-Host "Listen: OK ($listenHost)"
            }
        }
    }
} catch {
    Write-Host "Health: FALHOU $HealthUrl - $($_.Exception.Message)"
}

$listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
if ($listeners.Count -gt 0) {
    foreach ($listener in $listeners) {
        $status = if ($listener.LocalAddress -in @("127.0.0.1", "::1")) { "OK" } else { "EXPOSTO" }
        Write-Host "Porta: $status $($listener.LocalAddress):$($listener.LocalPort) pid=$($listener.OwningProcess)"
    }
} else {
    Write-Host "Porta: sem listener em $Port"
}

Show-Title "Modelos"
$checks = @(
    "models\diffusion_models",
    "models\unet",
    "models\vae",
    "models\text_encoders",
    "models\loras"
)
foreach ($rel in $checks) {
    $path = Join-Path $ComfyRoot $rel
    if (Test-Path $path) {
        $count = @(Get-ChildItem -LiteralPath $path -File -Recurse | Where-Object { $_.Extension -match "safetensors|gguf|pt|bin" }).Count
        Write-Host "$rel : OK ($count arquivos de modelo)"
    } else {
        Write-Host "$rel : AUSENTE"
    }
}

Show-Title "LoRA Videos"
$videoKit = Join-Path $LoraVideos "ritmos_animacao_kit\kit"
$trainer = Join-Path $LoraVideos "wan_lora_trainer"
Write-Host "Kit: $videoKit"
Write-Host "Trainer: $trainer"
if (Test-Path (Join-Path $videoKit "abertura_animada.mp4")) {
    $mp4 = Get-Item (Join-Path $videoKit "abertura_animada.mp4")
    Write-Host "Abertura atual: OK $([math]::Round($mp4.Length/1MB,2)) MB"
} else {
    Write-Host "Abertura atual: ausente"
}
if (Test-Path (Join-Path $trainer "config_ritmos_pixel_5b.yaml")) {
    Write-Host "Config treino: OK"
} else {
    Write-Host "Config treino: ausente"
}

Show-Title "Propaganda"
if (Test-Path (Join-Path $Marketing "produtos_reais_manifest.csv")) {
    $rows = Import-Csv (Join-Path $Marketing "produtos_reais_manifest.csv")
    $approved = @($rows | Where-Object { $_.source_image })
    Write-Host "Manifesto marketing: $($approved.Count)/$($rows.Count) com foto real"
} else {
    Write-Host "Manifesto marketing: ausente"
}

Show-Title "Sprunki"
if (Test-Path (Join-Path $Sprunki "logs\comfyui.watchdog.log")) {
    Write-Host "Watchdog ComfyUI log: OK"
    Get-Content (Join-Path $Sprunki "logs\comfyui.watchdog.log") -Tail 5
} else {
    Write-Host "Watchdog ComfyUI log: ausente"
}

Show-Title "Blindagem (regras 2026-07-19)"
$flagsDir = "E:\Pemara\maestro\pemara\dados\flags"
$lowvramFlag = Join-Path $flagsDir "comfy_lowvram_requested.flag"
if (Test-Path -LiteralPath $lowvramFlag) {
    $ageH = [math]::Round(((Get-Date) - (Get-Item -LiteralPath $lowvramFlag).LastWriteTime).TotalHours, 1)
    if ($ageH -gt 6) {
        Write-Host "ALERTA: flag lowvram com ${ageH}h (>6h). Ela se auto-remove no proximo boot do ComfyUI; remova ja se nao for smoke test ativo."
    } else {
        Write-Host "lowvram flag: ativa ha ${ageH}h (smoke test em andamento? expira em 6h)"
    }
} else {
    Write-Host "lowvram flag: ausente (OK)"
}
if (Test-Path -LiteralPath (Join-Path $flagsDir "training_paused.flag")) {
    Write-Host "Treinos: CONGELADOS por training_paused.flag (remover so com ordem do usuario)"
} else {
    Write-Host "Treinos: sem pausa global (janela 00:31-04:59 continua valendo)"
}
$wan5b = @(
    (Test-Path -LiteralPath (Join-Path $ComfyRoot "models\diffusion_models\wan2.2_ti2v_5B_fp16.safetensors")),
    (Test-Path -LiteralPath (Join-Path $ComfyRoot "lora_videos\ritmos_animacao_kit\kit\ComfyUI\models\diffusion_models\wan2.2_ti2v_5B_fp16.safetensors"))
) -contains $true
if ($wan5b) {
    Write-Host "ALERTA: Wan 5B TI2V presente no ComfyUI. Foi reprovado/quarentenado; nao usar."
} else {
    Write-Host "Wan 5B TI2V: ausente do ComfyUI (OK, quarentenado)"
}
$loras5b = @(Get-ChildItem -LiteralPath (Join-Path $ComfyRoot "models\loras") -Filter "intro_ritmos_60s_v1*.safetensors" -ErrorAction SilentlyContinue)
if ($loras5b.Count -gt 0) {
    Write-Host "ALERTA: $($loras5b.Count) LoRA(s) intro_ritmos_60s_v1 (base 5B) presentes; ficam em quarentena."
} else {
    Write-Host "LoRAs 5B intro_ritmos_60s_v1: ausentes (OK)"
}

Show-Title "Tarefas Agendadas"
$watchdogTask = Get-ScheduledTask -TaskName "Pemara ComfyUI Watchdog" -ErrorAction SilentlyContinue
$legacyComfyTask = Get-ScheduledTask -TaskName "PemaraComfyUI" -ErrorAction SilentlyContinue
if ($watchdogTask -and $legacyComfyTask -and
    $watchdogTask.State -ne "Disabled" -and $legacyComfyTask.State -ne "Disabled") {
    Write-Host "ALERTA: duas tarefas podem iniciar o ComfyUI. Desative PemaraComfyUI e mantenha somente o watchdog."
}
$tasks = @(
    "Pemara ComfyUI Watchdog",
    "PemaraComfyUI",
    "Pemara_Radar",
    "Pemara Marketing Fotos Reais",
    "RitmosTreinoWatchdog",
    "RitmosTreinoStart",
    "RitmosTreinoStop",
    "RitmosTreinoStartUser",
    "RitmosTreinoStopUser"
)
foreach ($task in $tasks) {
    $taskInfo = schtasks /Query /TN $task /FO LIST 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "${task}: sem permissao para consultar ou ausente"
        continue
    }

    $taskInfo | Select-String "Nome da tarefa|Status|Hora da" | ForEach-Object { $_.Line }
}
