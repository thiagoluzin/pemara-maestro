$ErrorActionPreference = "Stop"
$repo = "E:\Pemara\.agents\external_sources\token-skein"
$bun = "$env:LOCALAPPDATA\Microsoft\WinGet\Links\bun.exe"
$config = "E:\Pemara\.agents\token-skein\config.json"

if (!(Test-Path -LiteralPath $bun)) {
  throw "Bun nao encontrado em $bun. Reabra o terminal ou reinstale com winget install Oven-sh.Bun."
}

$env:TOKEN_SKEIN_CONFIG = $config
$env:TOKEN_SKEIN_DASHBOARD_PORT = "8790"
Set-Location -LiteralPath $repo
& $bun run dashboard
