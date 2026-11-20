$ErrorActionPreference = "Stop"
$operatorPython = Join-Path $env:LOCALAPPDATA 'Pemara/maestro-mcp/venv/Scripts/python.exe'
$workerScript = Join-Path (Split-Path $PSScriptRoot) 'services/studio/cinema_worker.py'
$command = Get-Command codex.exe -ErrorAction SilentlyContinue
if ($command) {
    $env:MAESTRO_CODEX_EXE = $command.Source
} else {
    $package = Get-AppxPackage -Name OpenAI.Codex | Sort-Object Version -Descending | Select-Object -First 1
    if ($package) { $env:MAESTRO_CODEX_EXE = Join-Path $package.InstallLocation 'app/resources/codex.exe' }
}
do {
    & $operatorPython $workerScript
} while ($LASTEXITCODE -eq 86)
exit $LASTEXITCODE

