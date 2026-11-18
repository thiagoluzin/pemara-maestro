$Target=Join-Path $env:LOCALAPPDATA 'ZICOAudioStudio'
$answer=Read-Host "Remover ZICO Audio Studio e ambientes? Digite REMOVER"
if ($answer -ne 'REMOVER') { Write-Host 'Cancelado.'; exit }
if (Test-Path $Target) { Remove-Item -LiteralPath $Target -Recurse -Force }
$shortcut=Join-Path ([Environment]::GetFolderPath('Desktop')) 'ZICO Audio Studio.lnk'
if (Test-Path $shortcut) { Remove-Item -LiteralPath $shortcut -Force }
Write-Host 'ZICO removido. Arquivos originais usados em projetos não foram apagados.'
