$ErrorActionPreference='Stop'
$flag='E:\Pemara\maestro\pemara\dados\logs\maestro_activation_20260913_1257.ready'
$log='E:\Pemara\maestro\pemara\dados\logs\maestro_activation_20260913_1257.log'
'Autorizacao administrativa recebida; aguardando liberacao da fila via MCP.' | Set-Content -LiteralPath $log -Encoding utf8
$deadline=(Get-Date).AddMinutes(15)
while ((Get-Date) -lt $deadline) {
    if (Test-Path -LiteralPath $flag) {
        $age=(Get-Date).ToUniversalTime()-(Get-Item -LiteralPath $flag).LastWriteTimeUtc
        if ($age.TotalSeconds -lt 15) {
            & 'E:\Pemara\maestro\pemara\services\studio\restart_studio.ps1'
            exit $LASTEXITCODE
        }
    }
    Start-Sleep -Seconds 1
}
'Prazo de espera encerrado sem reiniciar.' | Add-Content -LiteralPath $log
exit 2
