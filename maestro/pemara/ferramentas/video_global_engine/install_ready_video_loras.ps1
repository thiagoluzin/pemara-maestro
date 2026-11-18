param(
  [string]$Registry = "E:\Pemara\maestro\pemara\ferramentas\video_global_engine\templates\studio_video_model_registry.json",
  [string]$TargetDir = "E:\Pemara\maestro\pemara\ferramentas\ComfyUI\models\loras",
  [string[]]$Ids = @(),
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Registry)) {
  throw "Registry not found: $Registry"
}

$resolvedTarget = (Resolve-Path -LiteralPath $TargetDir -ErrorAction SilentlyContinue)
if (-not $resolvedTarget) {
  New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
  $resolvedTarget = Resolve-Path -LiteralPath $TargetDir
}

$data = Get-Content -LiteralPath $Registry -Raw | ConvertFrom-Json
$candidates = @($data.ready_lora_candidates | Where-Object {
  $identity = "{0}|{1}|{2}" -f $_.id, $_.repo, $_.base
  $identity -notmatch '(?i)wan|lightx2v'
})
if ($Ids.Count -gt 0) {
  $candidates = $candidates | Where-Object { $_.id -in $Ids }
}

if (-not $candidates -or $candidates.Count -eq 0) {
  throw "No LoRA candidates selected."
}

$python = Get-Command python -ErrorAction Stop

foreach ($item in $candidates) {
  $repo = [string]$item.repo
  $id = [string]$item.id
  $dest = Join-Path $resolvedTarget.Path "_ready_$id"
  Write-Host "== $id =="
  Write-Host "Repo: $repo"
  Write-Host "Destino: $dest"

  if ($DryRun) {
    continue
  }

  New-Item -ItemType Directory -Force -Path $dest | Out-Null
  $script = @"
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="$repo",
    local_dir=r"$dest",
    local_dir_use_symlinks=False,
    allow_patterns=["*.safetensors", "*.pt", "*.pth", "*.json", "*.md", "*.yaml", "*.yml"],
)
print(r"$dest")
"@
  $tmp = Join-Path $env:TEMP "pemara_download_$id.py"
  Set-Content -LiteralPath $tmp -Value $script -Encoding UTF8
  & $python.Source $tmp
  if ($LASTEXITCODE -ne 0) {
    throw "Download failed for $id"
  }
}
