[CmdletBinding()]
param(
    [switch]$SelfTest,
    [switch]$NoRestart
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $Root ".env"
$SessionFile = Join-Path $Root "dados\auth_sessions.json"
$BackupDir = Join-Path $Root "dados\secure_auth_backups"
$HashTool = Join-Path $PSScriptRoot "maestro_password_hash.py"
$RestartRequest = Join-Path $Root "solicitar_reinicio_maestro.ps1"
$RestartFallback = Join-Path $Root "reset_maestro_frontend.ps1"
$Python = (Get-Command python.exe -ErrorAction Stop).Source
$PowerShellExe = (Get-Command powershell.exe -ErrorAction Stop).Source
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Test-IsAdministrator {
    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object System.Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
}

function ConvertTo-PlainText {
    param([Parameter(Mandatory)] [System.Security.SecureString]$SecureValue)

    $pointer = [IntPtr]::Zero
    try {
        $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    } finally {
        if ($pointer -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
        }
    }
}

function Read-NewPassword {
    for ($attempt = 1; $attempt -le 5; $attempt++) {
        $firstSecure = Read-Host "Nova senha (minimo de 12 caracteres)" -AsSecureString
        $secondSecure = Read-Host "Repita a nova senha" -AsSecureString
        $first = ConvertTo-PlainText -SecureValue $firstSecure
        $second = ConvertTo-PlainText -SecureValue $secondSecure
        $firstSecure.Dispose()
        $secondSecure.Dispose()

        if ($first -cne $second) {
            $first = $null
            $second = $null
            Write-Host "As senhas nao conferem. Tente novamente." -ForegroundColor Yellow
            continue
        }
        $second = $null
        if ($first.Length -lt 12 -or $first.Length -gt 256) {
            $first = $null
            Write-Host "A senha deve possuir entre 12 e 256 caracteres." -ForegroundColor Yellow
            continue
        }
        if ([string]::IsNullOrWhiteSpace($first) -or $first.IndexOf([char]0) -ge 0) {
            $first = $null
            Write-Host "A senha informada nao e valida." -ForegroundColor Yellow
            continue
        }
        return $first
    }
    throw "Numero maximo de tentativas excedido."
}

function Invoke-HashTool {
    param(
        [Parameter(Mandatory)] [string]$Password,
        [string]$HashToVerify = ""
    )

    $passwordBytes = [System.Text.Encoding]::UTF8.GetBytes($Password)
    $payload = [Convert]::ToBase64String($passwordBytes)
    [Array]::Clear($passwordBytes, 0, $passwordBytes.Length)

    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = $Python
    $info.Arguments = '"' + $HashTool.Replace('"', '\"') + '"'
    if ($HashToVerify) {
        $info.Arguments += " --verify"
    }
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardInput = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $info
    try {
        if (-not $process.Start()) {
            throw "Nao foi possivel iniciar o gerador de hash."
        }
        $process.StandardInput.WriteLine($payload)
        if ($HashToVerify) {
            $process.StandardInput.WriteLine($HashToVerify)
        }
        $process.StandardInput.Close()
        $payload = $null
        $stdout = $process.StandardOutput.ReadToEnd().Trim()
        $stderr = $process.StandardError.ReadToEnd().Trim()
        $process.WaitForExit()
        if ($process.ExitCode -ne 0) {
            throw "Gerador de hash recusou a operacao: $stderr"
        }
        if ($HashToVerify) {
            return ($stdout -eq "OK")
        }
        if ($stdout -notmatch '^scrypt\$32768\$8\$1\$[A-Za-z0-9_-]+=*\$[A-Za-z0-9_-]+=*$') {
            throw "Formato de hash inesperado."
        }
        return $stdout
    } finally {
        $payload = $null
        $process.Dispose()
    }
}

function Get-MaestroAdminUser {
    param([Parameter(Mandatory)] [string]$Content)

    foreach ($line in [regex]::Split($Content, "\r\n|\n|\r")) {
        if ($line -match '^\s*MAESTRO_ADMIN_USER\s*=\s*(.*)$') {
            $value = $matches[1].Trim().Trim('"').Trim("'")
            if ($value) { return $value }
        }
    }
    return "admin"
}

function New-MaestroEnvContent {
    param(
        [Parameter(Mandatory)] [string]$Original,
        [Parameter(Mandatory)] [string]$PasswordHash
    )

    $newLine = if ($Original.Contains("`r`n")) { "`r`n" } elseif ($Original.Contains("`n")) { "`n" } else { [Environment]::NewLine }
    $hadTrailingNewLine = $Original.EndsWith("`r`n") -or $Original.EndsWith("`n") -or $Original.EndsWith("`r")
    $lines = [System.Collections.Generic.List[string]]::new()
    foreach ($line in [regex]::Split($Original, "\r\n|\n|\r")) { [void]$lines.Add($line) }
    if ($hadTrailingNewLine -and $lines.Count -gt 0 -and $lines[$lines.Count - 1] -eq "") {
        $lines.RemoveAt($lines.Count - 1)
    }

    $result = [System.Collections.Generic.List[string]]::new()
    $plainWritten = $false
    $hashWritten = $false
    foreach ($line in $lines) {
        if ($line -match '^\s*MAESTRO_ADMIN_PASSWORD\s*=') {
            if (-not $plainWritten) {
                [void]$result.Add("MAESTRO_ADMIN_PASSWORD=")
                $plainWritten = $true
            }
            continue
        }
        if ($line -match '^\s*MAESTRO_ADMIN_PASSWORD_HASH\s*=') {
            if (-not $hashWritten) {
                [void]$result.Add("MAESTRO_ADMIN_PASSWORD_HASH=$PasswordHash")
                $hashWritten = $true
            }
            continue
        }
        [void]$result.Add($line)
    }
    if (-not $plainWritten) { [void]$result.Add("MAESTRO_ADMIN_PASSWORD=") }
    if (-not $hashWritten) { [void]$result.Add("MAESTRO_ADMIN_PASSWORD_HASH=$PasswordHash") }

    $updated = [string]::Join($newLine, $result)
    if ($hadTrailingNewLine) { $updated += $newLine }
    return $updated
}

function Protect-BackupDirectory {
    New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
    $ownerSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    & icacls.exe $BackupDir "/inheritance:r" "/grant:r" `
        "*$ownerSid`:(OI)(CI)(F)" "*S-1-5-18:(OI)(CI)(F)" `
        "*S-1-5-32-544:(OI)(CI)(F)" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Nao foi possivel proteger a pasta de backup."
    }
}

function Write-SensitiveFileAtomically {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Content,
        [Parameter(Mandatory)] $Acl
    )

    $temp = "$Path.password_reset.$PID.tmp"
    try {
        [System.IO.File]::WriteAllText($temp, $Content, $Utf8NoBom)
        Set-Acl -LiteralPath $temp -AclObject $Acl
        Move-Item -LiteralPath $temp -Destination $Path -Force
        Set-Acl -LiteralPath $Path -AclObject $Acl
    } finally {
        if (Test-Path -LiteralPath $temp -PathType Leaf) {
            Remove-Item -LiteralPath $temp -Force
        }
    }
}

function Restart-MaestroFrontend {
    if ($NoRestart) { return }

    & $PowerShellExe -NoProfile -ExecutionPolicy Bypass -File $RestartRequest -Componente frontend -TimeoutSec 90
    if ($LASTEXITCODE -eq 0) { return }

    Write-Host "Supervisor indisponivel; aplicando reinicio local controlado do frontend." -ForegroundColor Yellow
    & $PowerShellExe -NoProfile -ExecutionPolicy Bypass -File $RestartFallback
    if ($LASTEXITCODE -ne 0) {
        throw "Nao foi possivel reiniciar o frontend do Maestro."
    }
}

function Get-MaestroLoginCsrfToken {
    param([Parameter(Mandatory)] [string]$Content)

    $pattern = '(?is)<input\b(?=[^>]*\bname\s*=\s*[''"]csrf_token[''"])(?=[^>]*\bvalue\s*=\s*[''"]([^''"]+)[''"])[^>]*>'
    $match = [regex]::Match($Content, $pattern)
    if (-not $match.Success) { return "" }
    return [System.Net.WebUtility]::HtmlDecode($match.Groups[1].Value)
}

function Test-MaestroHttpLogin {
    param(
        [Parameter(Mandatory)] [string]$Username,
        [Parameter(Mandatory)] [string]$Password
    )

    if ($NoRestart) { return $true }
    $baseUrl = "http://127.0.0.1:9501"
    $web = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    try {
        $login = Invoke-WebRequest -UseBasicParsing -Uri "$baseUrl/login" -WebSession $web -TimeoutSec 10
        $csrfToken = Get-MaestroLoginCsrfToken -Content $login.Content
        if (-not $csrfToken) {
            throw "Token CSRF da tela de login nao foi encontrado."
        }
        $body = @{
            usuario = $Username
            senha = $Password
            csrf_token = $csrfToken
        }
        $null = Invoke-WebRequest -UseBasicParsing -Uri "$baseUrl/login" -Method Post `
            -Body $body -ContentType "application/x-www-form-urlencoded" `
            -Headers @{ Origin = $baseUrl; "Sec-Fetch-Site" = "same-origin" } `
            -WebSession $web -TimeoutSec 15 -MaximumRedirection 5
        $health = Invoke-WebRequest -UseBasicParsing -Uri "$baseUrl/api/maestro/health" `
            -WebSession $web -TimeoutSec 10
        if ($health.StatusCode -ne 200) { return $false }
        try {
            $null = Invoke-WebRequest -UseBasicParsing -Uri "$baseUrl/logout" -Method Post `
                -WebSession $web -TimeoutSec 10 -MaximumRedirection 0 -ErrorAction SilentlyContinue
        } catch { }
        return $true
    } catch {
        Write-Host "Falha na validacao HTTP: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Invoke-SelfTest {
    $testPassword = "Maestro-SelfTest-2026!"
    $hash = Invoke-HashTool -Password $testPassword
    if (-not (Invoke-HashTool -Password $testPassword -HashToVerify $hash)) {
        throw "Self-test: hash gerado nao foi validado."
    }
    $sample = "A=1`r`nMAESTRO_ADMIN_PASSWORD=texto-antigo`r`nMAESTRO_ADMIN_PASSWORD_HASH=antigo`r`nMAESTRO_ADMIN_PASSWORD_HASH=duplicado`r`n"
    $updated = New-MaestroEnvContent -Original $sample -PasswordHash $hash
    $plainEntries = [regex]::Matches(
        $updated,
        '(?m)^[ \t]*MAESTRO_ADMIN_PASSWORD[ \t]*=([^\r\n]*)\r?$'
    )
    if ($plainEntries.Count -ne 1 -or $plainEntries[0].Groups[1].Value.Trim().Length -ne 0) {
        throw "Self-test: senha em texto puro permaneceu configurada."
    }
    if ([regex]::Matches($updated, '(?m)^MAESTRO_ADMIN_PASSWORD_HASH=').Count -ne 1) {
        throw "Self-test: hash duplicado."
    }
    if ($updated.Contains("texto-antigo") -or $updated.Contains("duplicado")) {
        throw "Self-test: valor legado permaneceu no arquivo."
    }
    $syntheticToken = "t" * 48
    $singleQuoted = "<input type='hidden' name='csrf_token' value='$syntheticToken'>"
    $doubleQuotedReordered = '<input value="' + $syntheticToken + '" type="hidden" name="csrf_token">'
    if ((Get-MaestroLoginCsrfToken -Content $singleQuoted) -cne $syntheticToken) {
        throw "Self-test: parser CSRF falhou com aspas simples."
    }
    if ((Get-MaestroLoginCsrfToken -Content $doubleQuotedReordered) -cne $syntheticToken) {
        throw "Self-test: parser CSRF falhou com atributos reordenados."
    }
    try {
        $liveLogin = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:9501/login" -TimeoutSec 10
        if (-not (Get-MaestroLoginCsrfToken -Content $liveLogin.Content)) {
            throw "formulario vivo sem csrf_token legivel"
        }
    } catch {
        throw "Self-test: formulario vivo do Maestro falhou: $($_.Exception.Message)"
    }
    Write-Host "SELFTEST_OK"
}

if ($SelfTest) {
    Invoke-SelfTest
    exit 0
}

if (-not (Test-IsAdministrator)) {
    throw "Execute pelo TROCAR_SENHA_MAESTRO.bat e aceite a elevacao do Windows."
}
if (-not (Test-Path -LiteralPath $EnvFile -PathType Leaf)) {
    throw "Arquivo .env do Maestro nao encontrado."
}
if (-not (Test-Path -LiteralPath $HashTool -PathType Leaf)) {
    throw "Gerador de hash nao encontrado."
}

$password = $null
$envBackup = $null
$sessionBackup = $null
$envAcl = Get-Acl -LiteralPath $EnvFile
$sessionAcl = if (Test-Path -LiteralPath $SessionFile -PathType Leaf) { Get-Acl -LiteralPath $SessionFile } else { $null }
$originalEnv = [System.IO.File]::ReadAllText($EnvFile, [System.Text.Encoding]::UTF8)
$username = Get-MaestroAdminUser -Content $originalEnv
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"

try {
    Write-Host "Usuario administrativo preservado: $username" -ForegroundColor Cyan
    $password = Read-NewPassword
    $passwordHash = Invoke-HashTool -Password $password
    if (-not (Invoke-HashTool -Password $password -HashToVerify $passwordHash)) {
        throw "O hash gerado nao passou na verificacao independente."
    }

    Protect-BackupDirectory
    $envBackup = Join-Path $BackupDir ".env.before_password_reset_$stamp"
    Copy-Item -LiteralPath $EnvFile -Destination $envBackup
    Set-Acl -LiteralPath $envBackup -AclObject $envAcl

    if ($sessionAcl) {
        $sessionBackup = Join-Path $BackupDir "auth_sessions.before_password_reset_$stamp.json"
        Copy-Item -LiteralPath $SessionFile -Destination $sessionBackup
        Set-Acl -LiteralPath $sessionBackup -AclObject $sessionAcl
    }

    $updatedEnv = New-MaestroEnvContent -Original $originalEnv -PasswordHash $passwordHash
    Write-SensitiveFileAtomically -Path $EnvFile -Content $updatedEnv -Acl $envAcl
    if ($sessionAcl) {
        Write-SensitiveFileAtomically -Path $SessionFile -Content "{}`r`n" -Acl $sessionAcl
    }

    $written = [System.IO.File]::ReadAllText($EnvFile, [System.Text.Encoding]::UTF8)
    $plainEntries = [regex]::Matches(
        $written,
        '(?m)^[ \t]*MAESTRO_ADMIN_PASSWORD[ \t]*=([^\r\n]*)\r?$'
    )
    if ($plainEntries.Count -ne 1 -or $plainEntries[0].Groups[1].Value.Trim().Length -ne 0) {
        throw "Verificacao falhou: senha em texto puro detectada."
    }
    if ([regex]::Matches($written, '(?m)^\s*MAESTRO_ADMIN_PASSWORD_HASH\s*=').Count -ne 1) {
        throw "Verificacao falhou: quantidade invalida de hashes ativos."
    }

    Restart-MaestroFrontend
    if (-not (Test-MaestroHttpLogin -Username $username -Password $password)) {
        throw "O frontend reiniciou, mas recusou a nova credencial."
    }

    Write-Host "" 
    Write-Host "SENHA ALTERADA E LOGIN VALIDADO." -ForegroundColor Green
    Write-Host "Usuario: $username"
    Write-Host "Backup protegido: $envBackup"
    Write-Host "As sessoes anteriores foram revogadas por seguranca."
    exit 0
} catch {
    Write-Host "Falha: $($_.Exception.Message)" -ForegroundColor Red
    if ($envBackup -and (Test-Path -LiteralPath $envBackup -PathType Leaf)) {
        Copy-Item -LiteralPath $envBackup -Destination $EnvFile -Force
        Set-Acl -LiteralPath $EnvFile -AclObject $envAcl
    }
    if ($sessionBackup -and (Test-Path -LiteralPath $sessionBackup -PathType Leaf)) {
        Copy-Item -LiteralPath $sessionBackup -Destination $SessionFile -Force
        Set-Acl -LiteralPath $SessionFile -AclObject $sessionAcl
    }
    try { Restart-MaestroFrontend } catch { }
    Write-Host "A configuracao anterior foi restaurada." -ForegroundColor Yellow
    exit 1
} finally {
    $password = $null
    $passwordHash = $null
    $originalEnv = $null
    $updatedEnv = $null
    $written = $null
}
