[CmdletBinding()]
param(
    [string]$TargetRoot = 'E:\Pemara',
    [string]$FoleyModelRoot = '',
    [switch]$RequireModels
)

$ErrorActionPreference = 'Stop'
$repo = Join-Path ([System.IO.Path]::GetFullPath($TargetRoot)) 'maestro\pemara'
$required = @(
    'services\studio\main.py',
    'services\studio\h3_prompt_writing.py',
    'services\studio\h3_workflow.py',
    'third_party\MiniMax-H3-official\skills\h3-prompt-writing\SKILL.md',
    'tools\model_installers\install_models.py',
    'tools\model_installers\models.lock.json',
    'tools\model_installers\INSTALAR_TUDO_MODELOS.bat',
    'tools\model_installers\VERIFICAR_MODELOS.bat'
)
foreach ($relative in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $repo $relative) -PathType Leaf)) { throw "Ausente: $relative" }
}

python -m py_compile (Join-Path $repo 'services\studio\main.py') (Join-Path $repo 'services\studio\h3_workflow.py')
node --check (Join-Path $repo 'app\assets\maestro.js')
Push-Location (Join-Path $repo 'services\studio')
try { python -m unittest test_h3_workflow test_h3_prompt_writing test_maestro_ui_contracts } finally { Pop-Location }
Push-Location (Join-Path $repo 'tools\model_installers')
try { python -m unittest test_install_models } finally { Pop-Location }
$encoders = (ffmpeg -hide_banner -encoders 2>&1 | Out-String)
if ($encoders -notmatch 'h264_nvenc') { throw 'FFmpeg sem h264_nvenc.' }
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
if (-not $RequireModels) {
    Write-Output 'PASS sistema local. Pesos nao foram exigidos; restaure-os separadamente antes de gerar.'
} else {
    $installerArgs = @(
        (Join-Path $repo 'tools\model_installers\install_models.py'),
        '--action', 'verify', '--component', 'all', '--target-root', ([System.IO.Path]::GetFullPath($TargetRoot))
    )
    if ($FoleyModelRoot) { $installerArgs += @('--foley-root', ([System.IO.Path]::GetFullPath($FoleyModelRoot)) ) }
    & python @installerArgs
    if ($LASTEXITCODE -ne 0) { throw "Verificacao dos modelos falhou com codigo $LASTEXITCODE." }
    Write-Output 'PASS sistema e modelos locais. O primeiro render continua exigindo janela de GPU e aprovacao humana.'
}
