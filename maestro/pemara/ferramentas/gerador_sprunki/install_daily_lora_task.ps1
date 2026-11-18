param(
    [string]$TaskName = "Pemara Sprunki LoRA Daily Training",
    [string]$Python = "python",
    [int]$Steps = 900,
    [int]$Dim = 8,
    [int]$Alpha = 8,
    [int]$BatchSize = 2,
    [double]$LearningRate = 0.00002,
    [int]$EvalSamples = 4,
    [string]$EvalStrengths = "0.15,0.30,0.45",
    [switch]$RunWhenLoggedOff,
    [string]$RunAsUser = "$env:USERDOMAIN\$env:USERNAME"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runner = Join-Path $Root "run_daily_lora_window.ps1"
$taskRun = "powershell.exe -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File `"$Runner`""
if ($Python -ne "python") {
    $taskRun += " -Python `"$Python`""
}
if (
    $Steps -ne 900 -or
    $Dim -ne 8 -or
    $Alpha -ne 8 -or
    $BatchSize -ne 2 -or
    $LearningRate -ne 0.00002 -or
    $EvalSamples -ne 4 -or
    $EvalStrengths -ne "0.15,0.30,0.45"
) {
    $taskRun += " -Steps $Steps -Dim $Dim -Alpha $Alpha -BatchSize $BatchSize -LearningRate $LearningRate -EvalSamples $EvalSamples -EvalStrengths `"$EvalStrengths`""
}

if ($RunWhenLoggedOff) {
    Write-Host "Modo deslogado ativado para $RunAsUser."
    Write-Host "A senha sera usada apenas para registrar a tarefa no Windows."
    $secure = Read-Host "Senha de $RunAsUser" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
        & schtasks.exe /Create /TN $TaskName /TR $taskRun /SC DAILY /ST 00:00 /RU $RunAsUser /RP $plain /RL HIGHEST /F | Out-Host
    } finally {
        if ($bstr -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }
        $plain = $null
    }
} else {
    & schtasks.exe /Create /TN $TaskName /TR $taskRun /SC DAILY /ST 00:00 /F | Out-Host
}
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao criar tarefa diaria de treino LoRA."
}

Write-Host "Tarefa instalada: $TaskName"
Write-Host "Horario: diariamente as 00:00"
Write-Host "Janela: 00:00 ate 04:00"
Write-Host "Preset seguro: steps=$Steps dim=$Dim alpha=$Alpha batch=$BatchSize lr=$LearningRate"
Write-Host "Avaliacao: $EvalSamples prompt(s), forcas $EvalStrengths"
if ($RunWhenLoggedOff) {
    Write-Host "Modo: executa mesmo com usuario deslogado."
}
Write-Host "Runner: $Runner"
