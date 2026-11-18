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

$pemaraSkills = @(
  "pemara-messenger-turbo",
  "pemara-ecosystem-orchestrator",
  "pemara-online-security-guardian",
  "pemara-cinematic-take-director",
  "pemara-video-production-lead",
  "pemara-music-production-lead",
  "pemara-music-songwriter",
  "pemara-music-arranger",
  "pemara-music-mix-engineer",
  "pemara-music-listening-qc",

  "pemara-cinematography-director",
  "pemara-performance-director",
  "pemara-film-editor",
  "pemara-live-action-combat-director",
  "pemara-live-action-kinetic-supervisor",
  "pemara-live-action-showrunner",
  "pemara-live-action-continuity",
  "pemara-live-action-qc",
  "pemara-video-motion-director",
  "pemara-voice-performance-director",
  "ai-video-intro-pipeline",
  "animation-engineer",
  "audio-analysis",
  "automation-engineer",
  "balance-tuner",
  "beatemup-combat-designer",
  "claude-context-audit",
  "code-archaeologist",
  "creative-director",
  "debugger",
  "demo-release-engineer",
  "game-audio-designer",
  "game-audio-reactive",
  "game-build-flow",
  "game-developer",
  "gamepad-input-specialist",
  "hero-sprite-scaling",
  "image-production",
  "level-designer",
  "modern-pixel-art-hd",
  "pack-doctor",
  "performance-optimizer",
  "phaser-16bit-platformer",
  "phaser-animation-turbo",
  "phaser-platformer-architect",
  "project-planner",
  "qa-automation-engineer",
  "saas-pentest-hardening",
  "sprite-animation",
  "sprite-image-reading",
  "sprunki-lora-trainer",
  "test-engineer",
  "vanilla-web-patterns",
  "video-production",
  "web-frontend-vanilla"
)

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
