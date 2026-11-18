param(
    [string[]]$Takes = @("02", "03", "04", "05"),
    [string]$TakesCsv = "",
    [string]$Label = "veo_kling_smoke_4s",
    [int]$Seconds = 4,
    [int]$Width = 768,
    [int]$Height = 432,
    [int]$Steps = 22,
    [double]$Guidance = 6.0
)

$ErrorActionPreference = "Continue"
if ($TakesCsv.Trim()) {
    $Takes = @($TakesCsv.Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ })
}
$Root = "E:\Pemara\maestro\pemara\ferramentas\video_intro_jogo"
$Flag = "E:\Pemara\maestro\pemara\dados\flags\video_generation_paused.flag"
$LogDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Log = Join-Path $LogDir "veo_kling_smoke_$Stamp.log"
$DisabledFlag = "$Flag.disabled_$Stamp"

function Write-RunLog {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $Log -Value $line -Encoding UTF8
    Write-Output $line
}

$exitCode = 1
try {
    if (Test-Path -LiteralPath $Flag) {
        Move-Item -LiteralPath $Flag -Destination $DisabledFlag -Force
        Write-RunLog "Flag de pausa suspensa temporariamente: $DisabledFlag"
    } else {
        Write-RunLog "Flag de pausa nao existia antes do teste."
    }

    Push-Location $Root
    $env:MAESTRO_STUDIO_URL = "http://127.0.0.1:8029"
    $args = @(
        ".\run_intro_take_queue.py",
        "--takes"
    ) + $Takes + @(
        "--assemble",
        "--max-take-seconds", "$Seconds",
        "--width", "$Width",
        "--height", "$Height",
        "--steps", "$Steps",
        "--guidance", "$Guidance",
        "--lora", "__none__",
        "--lora-strength", "0",
        "--motion-profile", "controlled",
        "--run-label", $Label,
        "--ignore-video-pause"
    )

    Write-RunLog "Iniciando: python $($args -join ' ')"
    & python @args 2>&1 | Tee-Object -FilePath $Log -Append
    $exitCode = $LASTEXITCODE
    Write-RunLog "Runner terminou com exit code $exitCode"
} finally {
    Pop-Location -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $DisabledFlag) {
        Move-Item -LiteralPath $DisabledFlag -Destination $Flag -Force
        Write-RunLog "Flag de pausa restaurada: $Flag"
    } elseif (-not (Test-Path -LiteralPath $Flag)) {
        "paused after explicit veo/kling smoke test on $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" |
            Set-Content -LiteralPath $Flag -Encoding UTF8
        Write-RunLog "Flag de pausa recriada: $Flag"
    } else {
        Write-RunLog "Flag de pausa ja estava ativa ao final."
    }
}

exit $exitCode
