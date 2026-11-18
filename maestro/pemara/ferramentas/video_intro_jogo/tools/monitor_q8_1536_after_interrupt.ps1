param(
    [Parameter(Mandatory = $true)]
    [int]$TargetPid,

    [Parameter(Mandatory = $true)]
    [string]$GpuLog,

    [Parameter(Mandatory = $true)]
    [string]$PauseFlag,

    [Parameter(Mandatory = $true)]
    [string]$PauseFlagBackup,

    [Parameter(Mandatory = $true)]
    [string]$DoneMarker
)

$ErrorActionPreference = "Continue"

if (-not (Test-Path -LiteralPath $GpuLog)) {
    "timestamp,name,memory.used [MiB],memory.free [MiB],utilization.gpu [%],temperature.gpu,power.draw [W]" |
        Set-Content -LiteralPath $GpuLog -Encoding ASCII
}

while (Get-Process -Id $TargetPid -ErrorAction SilentlyContinue) {
    try {
        $line = nvidia-smi --query-gpu=timestamp,name,memory.used,memory.free,utilization.gpu,temperature.gpu,power.draw --format=csv,noheader,nounits
        Add-Content -LiteralPath $GpuLog -Value $line -Encoding ASCII
    } catch {
        Add-Content -LiteralPath $GpuLog -Value ("LOG_ERROR," + $_.Exception.Message) -Encoding ASCII
    }
    Start-Sleep -Seconds 5
}

if ((Test-Path -LiteralPath $PauseFlagBackup) -and -not (Test-Path -LiteralPath $PauseFlag)) {
    Move-Item -LiteralPath $PauseFlagBackup -Destination $PauseFlag -Force
}

@{
    target_pid = $TargetPid
    finished_at = (Get-Date).ToString("s")
    gpu_log = $GpuLog
    pause_flag_restored = (Test-Path -LiteralPath $PauseFlag)
} | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $DoneMarker -Encoding UTF8
