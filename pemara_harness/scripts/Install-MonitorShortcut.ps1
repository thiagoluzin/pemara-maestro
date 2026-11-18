[CmdletBinding(PositionalBinding = $false)]
param(
  [string] $DesktopPath,
  [switch] $DryRun
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$launcher = Join-Path $projectRoot 'bin\Open-PemaraMonitor.ps1'
if ([string]::IsNullOrWhiteSpace($DesktopPath)) {
  $DesktopPath = [Environment]::GetFolderPath('Desktop')
}
if ([string]::IsNullOrWhiteSpace($DesktopPath)) {
  throw 'Nao foi possivel localizar a Area de Trabalho.'
}

$windowsRoot = $env:SystemRoot
if ([string]::IsNullOrWhiteSpace($windowsRoot)) { $windowsRoot = 'C:\Windows' }
$powerShell = Join-Path $windowsRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$shortcutPath = Join-Path $DesktopPath 'Pemara Harness Visual.lnk'
$arguments = "-NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$launcher`""

$report = [ordered]@{
  shortcutPath = $shortcutPath
  target = $powerShell
  arguments = $arguments
  workingDirectory = $projectRoot
  launcher = $launcher
  windowStyle = 'hidden'
}

if ($DryRun) {
  $report | ConvertTo-Json -Depth 3
  exit 0
}

if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
  throw "Launcher visual nao encontrado: $launcher"
}
if (-not (Test-Path -LiteralPath $DesktopPath -PathType Container)) {
  throw "Area de Trabalho nao encontrada: $DesktopPath"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $powerShell
$shortcut.Arguments = $arguments
$shortcut.WorkingDirectory = $projectRoot
$shortcut.Description = 'Abrir o monitor visual local do Pemara Harness'
$shortcut.IconLocation = "$powerShell,0"
$shortcut.WindowStyle = 1
$shortcut.Save()

$report | ConvertTo-Json -Depth 3
