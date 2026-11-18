$ErrorActionPreference = "Stop"
$repo = "E:\Pemara\.agents\external_sources\token-skein"
$bun = "$env:LOCALAPPDATA\Microsoft\WinGet\Links\bun.exe"
$config = "E:\Pemara\.agents\token-skein\config.json"

$env:TOKEN_SKEIN_CONFIG = $config
Set-Location -LiteralPath $repo
& $bun run src/cli.ts doctor
