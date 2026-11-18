$ErrorActionPreference = "Stop"

$watchdog = Join-Path $PSScriptRoot "watchdog_comfyui.ps1"
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    $watchdog,
    [ref]$tokens,
    [ref]$parseErrors
)

if ($parseErrors.Count -gt 0) {
    throw "watchdog_comfyui.ps1 possui erro de parse: $($parseErrors[0].Message)"
}

$invokeCheck = $ast.Find(
    {
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
        $node.Name -eq "Invoke-Check"
    },
    $true
)

if (-not $invokeCheck) {
    throw "Funcao Invoke-Check nao encontrada."
}

$portAssignments = @(
    $invokeCheck.Body.FindAll(
        {
            param($node)
            $node -is [System.Management.Automation.Language.AssignmentStatementAst] -and
            $node.Left -is [System.Management.Automation.Language.VariableExpressionAst] -and
            $node.Left.VariablePath.UserPath -ieq "Port"
        },
        $true
    )
)

if ($portAssignments.Count -gt 0) {
    throw "Invoke-Check nao pode atribuir a `$Port/`$port: isso sobrescreve a porta numerica do launcher."
}

if ($invokeCheck.Extent.Text -notmatch '(?i)"-Port"\s*,\s*"\$Port"') {
    throw "Invoke-Check deixou de encaminhar a porta canonica ao launcher."
}

if ($invokeCheck.Extent.Text -match '\|\s*Out-Null') {
    throw "Invoke-Check nao pode prender o launcher em pipe com Out-Null."
}

if ($invokeCheck.Extent.Text -notmatch '(?i)Start-Process') {
    throw "Invoke-Check deve iniciar o launcher sem bloquear o processo supervisor."
}

if ($invokeCheck.Extent.Text -notmatch '(?i)Get-TrackedComfyProcess') {
    throw "Invoke-Check deve preservar um processo Comfy rastreado durante computacao GPU."
}

if ($invokeCheck.Extent.Text -notmatch '(?i)UtilizationPercent') {
    throw "A protecao do render deve verificar utilizacao de compute, nao apenas VRAM alocada."
}

$comfyMain = Join-Path (Split-Path -Parent $PSScriptRoot) "ComfyUI\main.py"
$comfyMainText = Get-Content -Raw -LiteralPath $comfyMain
if ($comfyMainText -notmatch 'sys\.platform\s*==\s*"win32"' -or
    $comfyMainText -notmatch 'asyncio\.SelectorEventLoop\(\)') {
    throw "ComfyUI deve usar SelectorEventLoop no Windows para preservar o listener apos WinError 64."
}

$restartScript = Join-Path (Split-Path -Parent $PSScriptRoot) "ComfyUI\restart_comfy.ps1"
$restartText = Get-Content -Raw -LiteralPath $restartScript
if ($restartText -notmatch 'Get-CimInstance\s+Win32_Process' -or
    $restartText -notmatch '\$orphanPids') {
    throw "O reinicio administrativo deve remover workers ComfyUI orfaos sem listener."
}

Write-Output "PASS: watchdog preserva render ativo e ComfyUI usa listener Windows resiliente."
