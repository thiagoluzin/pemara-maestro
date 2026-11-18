$ErrorActionPreference = 'Stop'
$logRoot = 'D:\PemaraRuntimes\maestro-game-ai\logs'
Start-Transcript -Path "$logRoot\windows-dependencies.log" -Append
try {
    & winget.exe install --id BlenderFoundation.Blender --exact --silent --accept-package-agreements --accept-source-agreements --disable-interactivity
    if ($LASTEXITCODE -notin @(0,-1978335189)) { throw "Blender installation exit: $LASTEXITCODE" }
    $distros = (& wsl.exe --list --quiet) -replace "`0", ''
    if ($distros -notcontains 'Ubuntu-24.04') {
        & wsl.exe --install --distribution Ubuntu-24.04 --no-launch
        if ($LASTEXITCODE -ne 0) { throw "WSL Ubuntu installation exit: $LASTEXITCODE" }
    }
    Set-Content -LiteralPath "$logRoot\windows-dependencies.done" -Value (Get-Date -Format o)
} catch {
    $_ | Out-String | Set-Content -LiteralPath "$logRoot\windows-dependencies.error"
    throw
} finally { Stop-Transcript }
