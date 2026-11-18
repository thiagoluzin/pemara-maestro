param([int]$Port = 8188)
$ErrorActionPreference = 'Stop'
if ($Port -ne 8188) { throw 'Somente o runtime canonico 8188 e gerenciado aqui.' }
$python = 'E:\Pemara\maestro\pemara\ferramentas\comfy_mcp_runtime\Scripts\python.exe'
$controller = 'E:\Pemara\maestro\pemara\tools\comfy_lifecycle.py'
$flag = 'E:\Pemara\maestro\pemara\dados\flags\comfy_restart_requested.flag'
$log = 'E:\Pemara\maestro\pemara\dados\logs\restart_comfy_admin.log'
try {
    $request = if (Test-Path -LiteralPath $flag) { Get-Content -LiteralPath $flag -Raw } else { '' }
    if ($request.StartsWith('pemara-lifecycle-stop:')) {
        & $python $controller broker-stop 2>&1 | Out-File -LiteralPath $log -Append -Encoding utf8
        exit $LASTEXITCODE
    }
    # Legacy fixed restart requests use the same verified controller.
    & $python $controller stop 2>&1 | Out-File -LiteralPath $log -Append -Encoding utf8
    if ($LASTEXITCODE -ne 0) { throw 'Parada nao confirmada.' }
    # Consume the legacy request before the controller's explicit start.
    if (Test-Path -LiteralPath $flag) { Remove-Item -LiteralPath $flag }
    & $python $controller start 2>&1 | Out-File -LiteralPath $log -Append -Encoding utf8
    exit $LASTEXITCODE
} catch {
    Add-Content -LiteralPath $log -Value $_.Exception.Message
    exit 1
}
