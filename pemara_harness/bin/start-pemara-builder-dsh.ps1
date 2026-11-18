[CmdletBinding(PositionalBinding = $false)]
param(
  [Parameter(Mandatory = $true)]
  [string] $Workspace,

  [Parameter(Mandatory = $true)]
  [string] $Package,

  [string] $Task = '',

  [switch] $CheckOnly
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$workspaceRoot = (Resolve-Path -LiteralPath $Workspace).Path
$packagePath = (Resolve-Path -LiteralPath $Package).Path
$packageJson = Get-Content -LiteralPath $packagePath -Raw -Encoding UTF8
$packageObject = $packageJson | ConvertFrom-Json
$contractVersion = if ($null -eq $packageObject.contract_version) { 1 } else { [int] $packageObject.contract_version }
if ($contractVersion -notin @(1, 2)) {
  throw "Unsupported Builder contract version: $contractVersion"
}
$profileName = if ($contractVersion -eq 2) { 'pemara-builder-v2' } else { 'pemara-builder' }
$preflightCli = Join-Path $PSScriptRoot 'pemara-builder-prepare.mjs'
$dshRoot = (Resolve-Path -LiteralPath (Join-Path $projectRoot '..\third_party\deepseek-harness')).Path
$dshCli = Join-Path $dshRoot 'apps\cli\src\bin.ts'
$tsxLoaderPath = Join-Path $dshRoot 'node_modules\tsx\dist\esm\index.mjs'
$nodeUserInfoFallback = Join-Path $PSScriptRoot 'node-os-userinfo-fallback.cjs'
$profilePackage = Join-Path $projectRoot ".runtime\dsh-home-builder\profiles\$profileName\node_modules\@pemara\harness\package.json"

foreach ($requiredFile in @($preflightCli, $dshCli, $tsxLoaderPath, $nodeUserInfoFallback, $profilePackage)) {
  if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
    throw "Builder prerequisite missing: $requiredFile"
  }
}

$preflightArgs = @('--package', $packagePath, '--workspace', $workspaceRoot)
if ($CheckOnly) { $preflightArgs += '--check' }
$preflightOutput = & node $preflightCli @preflightArgs
if ($LASTEXITCODE -ne 0) {
  throw "Builder preflight rejected the run with exit code $LASTEXITCODE."
}
if ($CheckOnly) {
  $preflightOutput
  exit 0
}

$allowedPaths = ($packageObject.allowed_paths -join ', ')
$forbiddenPaths = ($packageObject.forbidden_paths -join ', ')
$skills = ($packageObject.skills -join ', ')
$stopConditions = ($packageObject.stop_conditions -join '; ')
$builderAuthority = if ($contractVersion -eq 2) {
  'Use somente builder_file_read, builder_file_write e builder_test_run para executar a obra. Nunca use shell ou Git bruto.'
}
else {
  'Produza somente conteúdo candidato para o host aplicar e verificar; este contrato não autoriza edição ou teste.'
}
$builderPrompt = @"
Execute this host-owned Pemara Builder contract.
Contract version: $contractVersion
Task id: $($packageObject.task_id)
Objective: $($packageObject.objective)
Allowed paths: $allowedPaths
Forbidden paths: $forbiddenPaths
Approved skills: $skills
Maximum rounds: $($packageObject.max_rounds)
Maximum changed files: $($packageObject.max_files_changed)
Network: denied. Service control: denied. GPU control: denied. Commit and publish: denied.
Stop conditions: $stopConditions

Use the durable task id above, begin each round, checkpoint concrete progress, and request completion
with evidence. The runtime is fail-closed. $builderAuthority Never claim promotion.
"@
if (-not [string]::IsNullOrWhiteSpace($Task)) {
  $builderPrompt += "`n<host_task>`n$Task`n</host_task>`n"
}

$previousDshHome = $env:DSH_HOME
$previousQwenApiKey = $env:PEMARA_QWEN_API_KEY
$previousTsxTsconfigPath = $env:TSX_TSCONFIG_PATH
$previousPermissionMode = $env:DSH_PERMISSION_MODE
$previousToolsMode = $env:DSH_TOOLS_MODE
$previousTelemetryMode = $env:DSH_TELEMETRY_MODE
$previousBuilderPackage = $env:PEMARA_BUILDER_PACKAGE
$previousBuilderWorkspace = $env:PEMARA_BUILDER_WORKSPACE
$previousBuilderContractVersion = $env:PEMARA_BUILDER_CONTRACT_VERSION

$env:DSH_HOME = Join-Path $projectRoot '.runtime\dsh-home-builder'
$env:TSX_TSCONFIG_PATH = Join-Path $dshRoot 'tsconfig.json'
$env:DSH_PERMISSION_MODE = 'read-only'
$env:DSH_TOOLS_MODE = 'native'
$env:DSH_TELEMETRY_MODE = 'DISABLED'
if ($contractVersion -eq 2) {
  $env:PEMARA_BUILDER_PACKAGE = $packagePath
  $env:PEMARA_BUILDER_WORKSPACE = $workspaceRoot
  $env:PEMARA_BUILDER_CONTRACT_VERSION = '2'
}
else {
  Remove-Item Env:PEMARA_BUILDER_PACKAGE -ErrorAction SilentlyContinue
  Remove-Item Env:PEMARA_BUILDER_WORKSPACE -ErrorAction SilentlyContinue
  $env:PEMARA_BUILDER_CONTRACT_VERSION = '1'
}
if ([string]::IsNullOrWhiteSpace($previousQwenApiKey)) {
  $env:PEMARA_QWEN_API_KEY = 'llama-local'
}

$tsxLoaderUrl = ([System.Uri] $tsxLoaderPath).AbsoluteUri
$dshExitCode = 1
Push-Location $workspaceRoot
try {
  & node --require $nodeUserInfoFallback --import $tsxLoaderUrl $dshCli --profile $profileName $builderPrompt
  $dshExitCode = $LASTEXITCODE
}
finally {
  Pop-Location
  $restore = @{
    DSH_HOME = $previousDshHome
    PEMARA_QWEN_API_KEY = $previousQwenApiKey
    TSX_TSCONFIG_PATH = $previousTsxTsconfigPath
    DSH_PERMISSION_MODE = $previousPermissionMode
    DSH_TOOLS_MODE = $previousToolsMode
    DSH_TELEMETRY_MODE = $previousTelemetryMode
    PEMARA_BUILDER_PACKAGE = $previousBuilderPackage
    PEMARA_BUILDER_WORKSPACE = $previousBuilderWorkspace
    PEMARA_BUILDER_CONTRACT_VERSION = $previousBuilderContractVersion
  }
  foreach ($entry in $restore.GetEnumerator()) {
    if ($null -eq $entry.Value) {
      Remove-Item -Path "Env:$($entry.Key)" -ErrorAction SilentlyContinue
    }
    else {
      Set-Item -Path "Env:$($entry.Key)" -Value $entry.Value
    }
  }
}

exit $dshExitCode
