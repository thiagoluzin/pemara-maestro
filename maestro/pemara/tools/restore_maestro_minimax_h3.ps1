[CmdletBinding()]
param(
    [string]$PackageRoot = $PSScriptRoot,
    [string]$TargetRoot = 'E:\Pemara',
    [switch]$AllowExisting
)

$ErrorActionPreference = 'Stop'
$package = (Resolve-Path -LiteralPath $PackageRoot).Path
$target = [System.IO.Path]::GetFullPath($TargetRoot)
if ([System.IO.Path]::GetPathRoot($target) -eq $target -or $target.Length -lt 6) { throw 'TargetRoot inseguro.' }
if ((Test-Path -LiteralPath $target) -and -not $AllowExisting) {
    $entries = @(Get-ChildItem -LiteralPath $target -Force -ErrorAction SilentlyContinue)
    if ($entries.Count) { throw 'TargetRoot nao esta vazio. Use uma pasta vazia ou -AllowExisting apos criar rollback.' }
}
& (Join-Path $package 'VALIDAR_BACKUP.ps1') -PackageRoot $package

function Copy-TreeChecked([string]$from, [string]$to) {
    New-Item -ItemType Directory -Path $to -Force | Out-Null
    & robocopy.exe $from $to /E /COPY:DAT /DCOPY:DAT /R:2 /W:2 /XJ /NFL /NDL /NJH /NJS /NP
    if ($LASTEXITCODE -gt 7) { throw "Robocopy falhou ($LASTEXITCODE): $from -> $to" }
}

Copy-TreeChecked (Join-Path $package 'payload\maestro') (Join-Path $target 'maestro')
Copy-TreeChecked (Join-Path $package 'payload\agents') (Join-Path $target '.agents')
$foleySource = Join-Path $package 'payload\models\HunyuanVideo-Foley'
$foleyTarget = Join-Path $target 'AI_Models\HunyuanVideo-Foley'
if (Test-Path -LiteralPath $foleySource) { Copy-TreeChecked $foleySource $foleyTarget }

$envExample = Join-Path $target 'maestro\pemara\.env.example'
$envFile = Join-Path $target 'maestro\pemara\.env'
if ((Test-Path -LiteralPath $envExample) -and -not (Test-Path -LiteralPath $envFile)) {
    $lines = Get-Content -LiteralPath $envExample
    $lines = $lines | ForEach-Object {
        if ($_ -like 'VIDEO_SOUND_HUNYUAN_MODEL_ROOT=*') { "VIDEO_SOUND_HUNYUAN_MODEL_ROOT=$foleyTarget" } else { $_ }
    }
    $lines | Set-Content -LiteralPath $envFile -Encoding utf8
}
Write-Output "RESTAURADO $target"
Write-Output 'Preencha os segredos no .env local e execute VALIDAR_INSTALACAO.ps1 antes de iniciar servicos.'
Write-Output "Depois rode: $target\maestro\pemara\tools\model_installers\INSTALAR_TUDO_MODELOS.bat"
