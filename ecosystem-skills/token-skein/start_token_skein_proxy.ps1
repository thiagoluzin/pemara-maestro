$ErrorActionPreference = "Stop"
$repo = "E:\Pemara\.agents\external_sources\token-skein"
$bun = "$env:LOCALAPPDATA\Microsoft\WinGet\Links\bun.exe"
$config = "E:\Pemara\.agents\token-skein\config.json"

if (!(Test-Path -LiteralPath $bun)) {
  throw "Bun nao encontrado em $bun. Reabra o terminal ou reinstale com winget install Oven-sh.Bun."
}
if (!(Test-Path -LiteralPath $repo)) {
  throw "Repositorio TokenSkein nao encontrado em $repo."
}
if (!(Test-Path -LiteralPath $config)) {
  throw "Config TokenSkein nao encontrada em $config."
}

$env:TOKEN_SKEIN_CONFIG = $config
Set-Location -LiteralPath $repo
& $bun run src/cli.ts proxy
