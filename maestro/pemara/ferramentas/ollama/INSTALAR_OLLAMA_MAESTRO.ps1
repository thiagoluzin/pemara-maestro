[CmdletBinding()]
param([switch]$DryRun)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$DownloadUrl = "https://ollama.com/download/OllamaSetup.exe"
$InstallRoot = [IO.Path]::GetFullPath("C:\PemaraAI\ollama")
$OllamaExe = Join-Path $InstallRoot "ollama.exe"
$ServerExe = Join-Path $InstallRoot "lib\ollama\llama-server.exe"
$OllamaHost = "127.0.0.1:11435"
$ModelsRoot = Join-Path $env:USERPROFILE ".ollama\models"
$Model = "qwen3.5:4b"
$MinimumFree = 12GB
$LogFile = $null

function Write-Log([string]$Message, [string]$Level = "INFO") {
    $line = "{0} [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level, $Message
    Write-Host $line
    if ($script:LogFile) {
        Add-Content -LiteralPath $script:LogFile -Value $line -Encoding UTF8
    }
}

function Assert-Preflight {
    $expected = [IO.Path]::GetFullPath("C:\PemaraAI\ollama").TrimEnd("\")
    if (-not [string]::Equals($InstallRoot.TrimEnd("\"), $expected, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Destino recusado: o Ollama do Maestro deve ficar em $expected."
    }
    if ($OllamaHost -ne "127.0.0.1:11435" -or $OllamaHost -match "0\.0\.0\.0") {
        throw "OLLAMA_HOST inseguro recusado."
    }
    $driveRoot = [IO.Path]::GetPathRoot($InstallRoot)
    $drive = Get-PSDrive -Name $driveRoot.TrimEnd(":\") -PSProvider FileSystem
    if ($null -eq $drive.Free -or $drive.Free -lt $MinimumFree) {
        $free = if ($null -eq $drive.Free) { "desconhecido" } else { [Math]::Round($drive.Free / 1GB, 1) }
        throw "Espaco insuficiente em $driveRoot ($free GB). Sao exigidos 12 GB livres."
    }
    Write-Log "Pre-flight aprovado: $([Math]::Round($drive.Free / 1GB, 1)) GB livres."
}

function Assert-NoActiveWork {
    $busy = Get-CimInstance Win32_Process -Filter "Name='ollama.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.CommandLine -and
            $_.CommandLine -match '(?i)\bollama\.exe"?\s+(pull|run|create|push|rm|cp)\b'
        }
    if ($busy) {
        $details = ($busy | ForEach-Object { "PID $($_.ProcessId): $($_.CommandLine)" }) -join "`n"
        throw "Ha trabalho Ollama ativo; aguarde para nao interrompe-lo:`n$details"
    }
}

function Set-UserConfiguration {
    $values = [ordered]@{
        OLLAMA_HOST = $OllamaHost
        OLLAMA_MODELS = $ModelsRoot
        MAESTRO_EDITOR_LLM_MODEL = $Model
    }
    foreach ($item in $values.GetEnumerator()) {
        [Environment]::SetEnvironmentVariable($item.Name, $item.Value, "User")
        Set-Item -LiteralPath "Env:\$($item.Name)" -Value $item.Value
        Write-Log "$($item.Name)=$($item.Value) configurado no usuario."
    }
}

function Download-OfficialInstaller([string]$Destination) {
    $uri = [Uri]$DownloadUrl
    if ($uri.Scheme -ne "https" -or $uri.Host -ne "ollama.com" -or $uri.AbsolutePath -ne "/download/OllamaSetup.exe") {
        throw "Fonte recusada. URL permitida: https://ollama.com/download/OllamaSetup.exe"
    }
    $lastError = $null
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        try {
            Write-Log "Baixando instalador oficial (tentativa $attempt/3)."
            Invoke-WebRequest -Uri $DownloadUrl -OutFile $Destination -UseBasicParsing -TimeoutSec 300
            if ((Get-Item -LiteralPath $Destination).Length -lt 1MB) {
                throw "Arquivo baixado pequeno demais."
            }
            return
        } catch {
            $lastError = $_
            if ($attempt -lt 3) { Start-Sleep -Seconds (2 * $attempt) }
        }
    }
    throw "Download falhou: $($lastError.Exception.Message)"
}

function Assert-OfficialSignature([string]$Path) {
    $signature = Get-AuthenticodeSignature -LiteralPath $Path
    if ($signature.Status -ne [Management.Automation.SignatureStatus]::Valid) {
        throw "Authenticode invalido: $($signature.Status)."
    }
    if (-not $signature.SignerCertificate) {
        throw "Certificado de assinatura ausente."
    }
    $organization = '(?i)(?:^|,\s*)O\s*=\s*"?Ollama Inc\.?"?(?:\s*,|$)'
    if ($signature.SignerCertificate.Subject -notmatch $organization) {
        throw "Organizacao da assinatura recusada: $($signature.SignerCertificate.Subject)"
    }
    Write-Log "Authenticode Valid e organizacao Ollama Inc. confirmados."
}

function Install-PerUser([string]$Installer) {
    $arguments = @(
        "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
        "/CURRENTUSER", "/SP-", "/DIR=$InstallRoot"
    )
    $process = Start-Process -FilePath $Installer -ArgumentList $arguments -Wait -PassThru
    if ($process.ExitCode -notin @(0, 3010)) {
        throw "O instalador terminou com codigo $($process.ExitCode)."
    }
    foreach ($required in @($OllamaExe, $ServerExe)) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
            throw "Executavel obrigatorio ausente: $required"
        }
        Write-Log "Validado: $required"
    }
}

function Stop-KnownServer {
    Get-CimInstance Win32_Process -Filter "Name='ollama.exe'" -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ExecutablePath -and
            [string]::Equals([IO.Path]::GetFullPath($_.ExecutablePath), $OllamaExe, [StringComparison]::OrdinalIgnoreCase) -and
            $_.CommandLine -match '(?i)\sserve(?:\s|$)'
        } |
        ForEach-Object {
            Write-Log "Reiniciando servidor Ollama conhecido (PID $($_.ProcessId))."
            Stop-Process -Id $_.ProcessId -Force
        }
}

function Start-OllamaSafely {
    $radar = Get-ScheduledTask -TaskName "Pemara_Radar" -ErrorAction SilentlyContinue |
        Where-Object { $_.TaskPath -eq "\" } |
        Select-Object -First 1
    if ($radar) {
        Write-Log "Reutilizando Pemara_Radar; nenhum watchdog novo sera criado."
        if ($radar.State -eq "Running") {
            Stop-ScheduledTask -TaskName "Pemara_Radar" -TaskPath "\"
            $limit = (Get-Date).AddSeconds(20)
            do {
                Start-Sleep -Milliseconds 500
                $radar = Get-ScheduledTask -TaskName "Pemara_Radar" -TaskPath "\"
            } while ($radar.State -eq "Running" -and (Get-Date) -lt $limit)
            if ($radar.State -eq "Running") { throw "O Radar nao encerrou em 20 segundos." }
        }
        Start-ScheduledTask -TaskName "Pemara_Radar" -TaskPath "\"
    } else {
        Write-Log "Pemara_Radar ausente; iniciando diretamente, sem criar watchdog." "WARN"
        Start-Process -FilePath $OllamaExe -ArgumentList "serve" -WorkingDirectory $InstallRoot -WindowStyle Hidden
    }
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        try {
            $null = Invoke-RestMethod "http://$OllamaHost/api/tags" -TimeoutSec 4
            Write-Log "Ollama saudavel em http://$OllamaHost (loopback)."
            return
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    throw "Ollama nao respondeu em http://$OllamaHost/api/tags dentro de 60 segundos."
}

Assert-Preflight
if ($DryRun) {
    Write-Log "DRY-RUN: nenhuma alteracao, download ou instalacao sera feita."
    Write-Log "Fonte: $DownloadUrl"
    Write-Log "Destino: $InstallRoot"
    Write-Log "Modelos preservados: $ModelsRoot"
    Write-Log "Endpoint: http://$OllamaHost"
    Write-Log "Modelo do Editor IA: $Model"
    exit 0
}

$logRoot = "C:\PemaraAI\logs"
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
$script:LogFile = Join-Path $logRoot "instalar_ollama_maestro.log"
Assert-NoActiveWork
Set-UserConfiguration

$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ("maestro-ollama-" + [Guid]::NewGuid().ToString("N"))
$installer = Join-Path $tempRoot "OllamaSetup.exe"
try {
    New-Item -ItemType Directory -Path $tempRoot | Out-Null
    Download-OfficialInstaller $installer
    Assert-OfficialSignature $installer
    Install-PerUser $installer
    Stop-KnownServer
    Start-OllamaSafely
    Write-Log "Instalacao do Ollama para o Maestro concluida."
} finally {
    if (Test-Path -LiteralPath $installer -PathType Leaf) {
        Remove-Item -LiteralPath $installer -Force
        Write-Log "Instalador temporario proprio removido."
    }
    if ((Test-Path -LiteralPath $tempRoot -PathType Container) -and
        -not (Get-ChildItem -LiteralPath $tempRoot -Force)) {
        Remove-Item -LiteralPath $tempRoot -Force
    }
}
