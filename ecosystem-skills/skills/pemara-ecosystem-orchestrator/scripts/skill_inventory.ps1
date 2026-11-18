param(
  [string]$SkillsRoot = "E:\Pemara\.agents\skills",
  [string]$Validator = "C:\Users\admin_remoto\.codex\skills\.system\skill-creator\scripts\quick_validate.py",
  [switch]$PemaraOnly,
  [switch]$Validate
)

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"

if (-not (Test-Path -LiteralPath $SkillsRoot)) {
  throw "Skills root not found: $SkillsRoot"
}

$rows = @()

# The registry owns the public profiles. Standalone project skills have no profile.
if ($PemaraOnly) {
  $registryPath = Join-Path $SkillsRoot 'pemara-messenger-turbo/references/turbo_registry.json'
  $registry = Get-Content -LiteralPath $registryPath -Raw -Encoding UTF8 | ConvertFrom-Json
  $standaloneSkills = @(
    'pemara-ecosystem-orchestrator',
    'pemara-messenger-turbo',
    'pemara-cinematic-take-director',
    'pemara-video-motion-director',
    'saas-pentest-hardening',
    'ffviii-gunblade-duel-production'
  )
  $pemaraSkills = @($registry.aliases) + @($registry.specialized_profiles) + $standaloneSkills
  foreach ($name in $pemaraSkills) {
    if (-not (Test-Path -LiteralPath (Join-Path $SkillsRoot "$name/SKILL.md") -PathType Leaf)) {
      throw "Registered skill not found: $name"
    }
  }
}

Get-ChildItem -LiteralPath $SkillsRoot -Directory | ForEach-Object {
  if ($PemaraOnly -and ($_.Name -notin $pemaraSkills)) {
    return
  }

  $skillDir = $_.FullName
  $skillMd = Join-Path $skillDir "SKILL.md"
  if (-not (Test-Path -LiteralPath $skillMd)) {
    return
  }

  # Windows PowerShell 5.1 treats UTF-8 files without BOM as ANSI unless the
  # encoding is explicit, which corrupts Portuguese text during inspection.
  $lineCount = (Get-Content -LiteralPath $skillMd -Encoding UTF8 | Measure-Object -Line).Lines
  $hasAgent = Test-Path -LiteralPath (Join-Path $skillDir "agents\openai.yaml")
  $hasRefs = Test-Path -LiteralPath (Join-Path $skillDir "references")
  $hasScripts = Test-Path -LiteralPath (Join-Path $skillDir "scripts")
  $status = "not-validated"

  if ($Validate) {
    & python $Validator $skillDir *> $null
    if ($LASTEXITCODE -eq 0) {
      $status = "valid"
    } else {
      $status = "invalid"
    }
  }

  $rows += [PSCustomObject]@{
    Skill = $_.Name
    Lines = $lineCount
    HasOpenAIYaml = $hasAgent
    HasReferences = $hasRefs
    HasScripts = $hasScripts
    NeedsSplit = ($lineCount -gt 150)
    Status = $status
  }
}

$rows | Sort-Object `
  @{ Expression = "NeedsSplit"; Descending = $true }, `
  @{ Expression = "Lines"; Descending = $true }, `
  @{ Expression = "Skill"; Descending = $false }
