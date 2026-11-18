[CmdletBinding(PositionalBinding = $false)]
param(
  [string] $Workspace = (Get-Location).Path,
  [string] $TaskFile,
  [string] $MediaContextPath,
  [ValidateSet('local-qwen', 'deepseek-api')]
  [string] $ProviderId = 'local-qwen',

  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]] $TaskArgs
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$workspaceRoot = (Resolve-Path -LiteralPath $Workspace).Path
$workspaceItem = Get-Item -LiteralPath $workspaceRoot
if (-not $workspaceItem.PSIsContainer) {
  throw "Workspace is not a directory: $workspaceRoot"
}

$dshRoot = (Resolve-Path -LiteralPath (Join-Path $projectRoot '..\third_party\deepseek-harness')).Path
$dshCli = Join-Path $dshRoot 'apps\cli\src\bin.ts'
$tsxLoaderPath = Join-Path $dshRoot 'node_modules\tsx\dist\esm\index.mjs'
$nodeUserInfoFallback = Join-Path $PSScriptRoot 'node-os-userinfo-fallback.cjs'
$tsxTsconfigPath = Join-Path $dshRoot 'tsconfig.json'
$profileRoot = Join-Path $projectRoot '.runtime\dsh-home\profiles\pemara'
$profilePackage = Join-Path $profileRoot 'node_modules\@pemara\harness\package.json'

if (-not [string]::IsNullOrWhiteSpace($TaskFile)) {
  $TaskFile = (Resolve-Path -LiteralPath $TaskFile).Path
  $monitorRuntime = [IO.Path]::GetFullPath((Join-Path $projectRoot '.runtime\monitor')).TrimEnd('\') + '\'
  if (-not $TaskFile.StartsWith($monitorRuntime, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'TaskFile precisa ficar no runtime isolado do monitor.'
  }
}
if (-not [string]::IsNullOrWhiteSpace($MediaContextPath)) {
  $MediaContextPath = (Resolve-Path -LiteralPath $MediaContextPath).Path
  $monitorRuntime = [IO.Path]::GetFullPath((Join-Path $projectRoot '.runtime\monitor')).TrimEnd('\') + '\'
  if (-not $MediaContextPath.StartsWith($monitorRuntime, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'MediaContextPath precisa ficar no runtime isolado do monitor.'
  }
}

if (-not (Test-Path -LiteralPath $dshCli -PathType Leaf)) {
  throw "DeepSeek Harness source CLI not found: $dshCli"
}
if (-not (Test-Path -LiteralPath $tsxLoaderPath -PathType Leaf)) {
  throw "DeepSeek Harness TSX loader not found: $tsxLoaderPath"
}
if (-not (Test-Path -LiteralPath $tsxTsconfigPath -PathType Leaf)) {
  throw "DeepSeek Harness tsconfig not found: $tsxTsconfigPath"
}
if (-not (Test-Path -LiteralPath $nodeUserInfoFallback -PathType Leaf)) {
  throw "Node Windows compatibility preload not found: $nodeUserInfoFallback"
}
$tsxLoaderUrl = ([System.Uri] $tsxLoaderPath).AbsoluteUri

if (-not (Test-Path -LiteralPath $profilePackage)) {
  Push-Location $profileRoot
  try {
    & corepack pnpm install --ignore-scripts
    if ($LASTEXITCODE -ne 0) { throw "Profile dependency install failed with exit code $LASTEXITCODE." }
  }
  finally {
    Pop-Location
  }
}

$previousDshHome = $env:DSH_HOME
$previousQwenApiKey = $env:PEMARA_QWEN_API_KEY
$previousModelProvider = $env:PEMARA_MODEL_PROVIDER
$previousModelId = $env:PEMARA_MODEL_ID
$previousTsxTsconfigPath = $env:TSX_TSCONFIG_PATH
$previousMediaContextPath = $env:PEMARA_MEDIA_CONTEXT_PATH
$previousTaskFile = $env:PEMARA_TASK_FILE
$env:DSH_HOME = Join-Path $projectRoot '.runtime\dsh-home'
$env:TSX_TSCONFIG_PATH = Join-Path $dshRoot 'tsconfig.json'
if ([string]::IsNullOrWhiteSpace($previousQwenApiKey)) {
  # llama-server requires a non-empty OpenAI-compatible key value but performs
  # no remote authentication. Keep the placeholder local to this child launch.
  $env:PEMARA_QWEN_API_KEY = 'llama-local'
}
if ($ProviderId -eq 'deepseek-api') {
  if ([string]::IsNullOrWhiteSpace($env:DEEPSEEK_API_KEY)) {
    throw 'DeepSeek API selecionada, mas DEEPSEEK_API_KEY não está configurada neste processo.'
  }
  $env:PEMARA_MODEL_PROVIDER = 'pemara-deepseek'
  $env:PEMARA_MODEL_ID = 'deepseek-chat'
}
else {
  $env:PEMARA_MODEL_PROVIDER = 'pemara-qwen38'
  $env:PEMARA_MODEL_ID = 'qwen3.8-27b-uncensored-yarn-524k'
}
if ([string]::IsNullOrWhiteSpace($MediaContextPath)) {
  Remove-Item Env:PEMARA_MEDIA_CONTEXT_PATH -ErrorAction SilentlyContinue
}
else {
  $env:PEMARA_MEDIA_CONTEXT_PATH = $MediaContextPath
}
if ([string]::IsNullOrWhiteSpace($TaskFile)) {
  Remove-Item Env:PEMARA_TASK_FILE -ErrorAction SilentlyContinue
}
else {
  $env:PEMARA_TASK_FILE = $TaskFile
}
$dshExitCode = 1
Push-Location $workspaceRoot
try {
  # Execute the official source CLI directly so process.cwd(), the filesystem
  # sandbox, instructions and skill discovery all belong to the chosen workspace.
  # The official source entry maps workspace packages whose local Host artifacts
  # are intentionally not all built; TSX is addressed by file URL on Windows.
  & node --require $nodeUserInfoFallback --import $tsxLoaderUrl $dshCli --profile pemara @TaskArgs
  $dshExitCode = $LASTEXITCODE
}
finally {
  Pop-Location
  if ($null -eq $previousDshHome) {
    Remove-Item Env:DSH_HOME -ErrorAction SilentlyContinue
  }
  else {
    $env:DSH_HOME = $previousDshHome
  }
  if ($null -eq $previousQwenApiKey) {
    Remove-Item Env:PEMARA_QWEN_API_KEY -ErrorAction SilentlyContinue
  }
  else {
    $env:PEMARA_QWEN_API_KEY = $previousQwenApiKey
  }
  if ($null -eq $previousModelProvider) {
    Remove-Item Env:PEMARA_MODEL_PROVIDER -ErrorAction SilentlyContinue
  }
  else {
    $env:PEMARA_MODEL_PROVIDER = $previousModelProvider
  }
  if ($null -eq $previousModelId) {
    Remove-Item Env:PEMARA_MODEL_ID -ErrorAction SilentlyContinue
  }
  else {
    $env:PEMARA_MODEL_ID = $previousModelId
  }
  if ($null -eq $previousTsxTsconfigPath) {
    Remove-Item Env:TSX_TSCONFIG_PATH -ErrorAction SilentlyContinue
  }
  else {
    $env:TSX_TSCONFIG_PATH = $previousTsxTsconfigPath
  }
  if ($null -eq $previousMediaContextPath) {
    Remove-Item Env:PEMARA_MEDIA_CONTEXT_PATH -ErrorAction SilentlyContinue
  }
  else {
    $env:PEMARA_MEDIA_CONTEXT_PATH = $previousMediaContextPath
  }
  if ($null -eq $previousTaskFile) {
    Remove-Item Env:PEMARA_TASK_FILE -ErrorAction SilentlyContinue
  }
  else {
    $env:PEMARA_TASK_FILE = $previousTaskFile
  }
}

exit $dshExitCode
