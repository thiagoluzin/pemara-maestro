[CmdletBinding()]
param(
    [ValidateSet('Apply', 'Restore')][string]$Action = 'Apply',
    [switch]$InstallAtLogon
)

$ErrorActionPreference = 'Stop'
$gpuId = 'GPU-25c376f3-5fba-6bc9-2847-02f99f953eb8'
$smi = 'C:\Windows\System32\nvidia-smi.exe'
$stateDir = Join-Path $PSScriptRoot 'state'
$snapshotPath = Join-Path $stateDir 'before-cool-profile.json'
$resultPath = Join-Path $stateDir 'last-result.json'
$taskName = 'Pemara RTX 5090 Cool Profile 500W'
$legacyTaskName = 'Pemara RTX 5090 Cool Profile 400W'
$targetWatts = 500
New-Item -ItemType Directory -Path $stateDir -Force | Out-Null

function Get-GpuSnapshot {
    $output = @(& $smi -i $gpuId '--query-gpu=uuid,name,power.limit,power.default_limit,power.min_limit,power.max_limit,temperature.gpu' '--format=csv,noheader,nounits' 2>&1)
    if ($LASTEXITCODE -ne 0) { throw "NVIDIA query failed: $($output -join ' ')" }
    $fields = ($output -join '').Split(',') | ForEach-Object { $_.Trim() }
    if ($fields.Count -ne 7 -or $fields[0] -ne $gpuId -or $fields[1] -ne 'NVIDIA GeForce RTX 5090') {
        throw 'Unexpected GPU identity or telemetry format.'
    }
    $culture = [Globalization.CultureInfo]::InvariantCulture
    return [ordered]@{
        uuid = $fields[0]; name = $fields[1]
        powerLimitWatts = [double]::Parse($fields[2], $culture)
        defaultPowerLimitWatts = [double]::Parse($fields[3], $culture)
        minPowerLimitWatts = [double]::Parse($fields[4], $culture)
        maxPowerLimitWatts = [double]::Parse($fields[5], $culture)
        temperatureC = [double]::Parse($fields[6], $culture)
    }
}

$result = [ordered]@{createdAt=(Get-Date).ToString('o'); action=$Action; status='PENDING'; gpuUuid=$gpuId}
try {
    $principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Administrator elevation is required to change NVIDIA power limits.'
    }
    $before = Get-GpuSnapshot
    $result.before = $before
    if ($Action -eq 'Apply') {
        if ($targetWatts -lt $before.minPowerLimitWatts -or $targetWatts -gt $before.maxPowerLimitWatts) {
            throw '500 W is outside this GPU reported limits.'
        }
        if (-not (Test-Path -LiteralPath $snapshotPath)) {
            $before | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $snapshotPath -Encoding UTF8
        }
        $setWatts = $targetWatts
    } else {
        $original = Get-Content -LiteralPath $snapshotPath -Raw | ConvertFrom-Json
        if ($original.uuid -ne $gpuId) { throw 'Rollback GPU identity mismatch.' }
        $setWatts = [double]$original.powerLimitWatts
        if ($setWatts -lt $before.minPowerLimitWatts -or $setWatts -gt $before.maxPowerLimitWatts) {
            throw 'Saved rollback limit is outside current GPU limits.'
        }
    }
    $output = @(& $smi -i $gpuId -pl ([string]$setWatts) 2>&1)
    $result.driverOutput = $output -join "`n"
    if ($LASTEXITCODE -ne 0) { throw "NVIDIA refused power limit: $($output -join ' ')" }
    $after = Get-GpuSnapshot
    if ([Math]::Abs($after.powerLimitWatts - $setWatts) -gt 0.5) { throw 'Driver readback did not confirm requested power limit.' }
    $result.after = $after
    $result.voltageChanged = $false
    $result.clocksChanged = $false
    $result.fanPolicyChanged = $false
    $result.temperatureTarget = 'Hardware target unsupported; R17 software guard warns at 80 C and requests cancellation at 85 C, not a physical temperature clamp.'
    if ($Action -eq 'Apply' -and $InstallAtLogon) {
        $userName = [Security.Principal.WindowsIdentity]::GetCurrent().Name
        $shell = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
        $argsText = '-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "{0}" -Action Apply' -f $PSCommandPath
        $taskAction = New-ScheduledTaskAction -Execute $shell -Argument $argsText
        $trigger = New-ScheduledTaskTrigger -AtLogOn -User $userName
        $taskPrincipal = New-ScheduledTaskPrincipal -UserId $userName -LogonType Interactive -RunLevel Highest
        $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -StartWhenAvailable
        Register-ScheduledTask -TaskName $taskName -Action $taskAction -Trigger $trigger -Principal $taskPrincipal -Settings $settings -Description 'Restore the verified 500 W ceiling for the specific Pemara RTX 5090 at user logon. No render, voltage change or overclock.' -Force | Out-Null
        $result.atLogonTask = $taskName
        $legacyTask = Get-ScheduledTask -TaskName $legacyTaskName -ErrorAction SilentlyContinue
        if ($legacyTask) {
            if (@($legacyTask.Actions).Count -ne 1 -or $legacyTask.Actions[0].Arguments -notlike ('*"' + $PSCommandPath + '"*')) {
                throw 'Legacy task action is not owned by this profile; refusing to remove it.'
            }
            Unregister-ScheduledTask -TaskName $legacyTaskName -Confirm:$false
            $result.replacedAtLogonTask = $legacyTaskName
        }
    }
    if ($Action -eq 'Restore') {
        foreach ($ownedTaskName in @($taskName, $legacyTaskName)) {
            $task = Get-ScheduledTask -TaskName $ownedTaskName -ErrorAction SilentlyContinue
            if ($task) {
                if (@($task.Actions).Count -ne 1 -or $task.Actions[0].Arguments -notlike ('*"' + $PSCommandPath + '"*')) {
                    throw 'Task action is not owned by this profile; refusing to remove it.'
                }
                Unregister-ScheduledTask -TaskName $ownedTaskName -Confirm:$false
            }
        }
    }
    $result.status = 'PASS_DRIVER_READBACK'
} catch {
    $result.status = 'FAILED'
    $result.error = $_.Exception.Message
} finally {
    $result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $resultPath -Encoding UTF8
    $result | ConvertTo-Json -Depth 6
}
if ($result.status -ne 'PASS_DRIVER_READBACK') { exit 1 }
