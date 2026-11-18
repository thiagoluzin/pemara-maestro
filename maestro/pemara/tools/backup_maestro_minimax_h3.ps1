[CmdletBinding()]
param(
    [string]$SourceRoot = 'E:\Pemara\maestro\pemara',
    [string]$AgentsRoot = 'E:\Pemara\.agents',
    [string]$DestinationRoot = 'G:\Pemara_Backups',
    [string]$FoleyModelRoot = 'G:\Pemara_AI_Models\HunyuanVideo-Foley',
    [bool]$IncludeModels = $false
)

$ErrorActionPreference = 'Stop'
$source = (Resolve-Path -LiteralPath $SourceRoot).Path
$agents = (Resolve-Path -LiteralPath $AgentsRoot).Path
$destinationBase = (Resolve-Path -LiteralPath $DestinationRoot).Path
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$package = Join-Path $destinationBase "Maestro_MiniMax_H3_System_$stamp"
$payload = Join-Path $package 'payload'
$codeDestination = Join-Path $payload 'maestro\pemara'
$agentsDestination = Join-Path $payload 'agents'
$foleyDestination = Join-Path $payload 'models\HunyuanVideo-Foley'

if ($package -eq $destinationBase -or $package.Length -le $destinationBase.Length) {
    throw 'Destino de backup inseguro.'
}
New-Item -ItemType Directory -Path $codeDestination, $agentsDestination -Force | Out-Null

function Invoke-RobocopyChecked {
    param([string]$From, [string]$To, [string[]]$Extra = @())
    New-Item -ItemType Directory -Path $To -Force | Out-Null
    & robocopy.exe $From $To /E /COPY:DAT /DCOPY:DAT /R:2 /W:2 /XJ /NFL /NDL /NJH /NJS /NP @Extra
    if ($LASTEXITCODE -gt 7) {
        throw "Robocopy falhou ($LASTEXITCODE): $From -> $To"
    }
}

# Backup de sistema significa codigo, configuracao e ferramentas, sem qualquer
# peso de inferencia. Isto cobre tambem modelos auxiliares que vivem fora de
# ComfyUI/models (DWPose, Depth Anything, RIFE, RealESRGAN e LoRAs antigos).

$rootFiles = @(
    '.env.example', 'FIXLOG.md', 'GERADORES_STUDIO.md', 'MAESTRO_PRO_DEPLOY.md',
    'MASTER.py', 'NVIDIA_SKILLS_TRIAGEM.md', 'PLANO_RTX5090_QUALIDADE_MAXIMA.md',
    'reset_maestro_frontend.ps1', 'solicitar_reinicio_maestro.ps1',
    'test_master_auth.py', 'test_master_proxy.py', 'test_qwen_auto_release_ui.py'
)
foreach ($name in $rootFiles) {
    $from = Join-Path $source $name
    if (Test-Path -LiteralPath $from -PathType Leaf) { Copy-Item -LiteralPath $from -Destination (Join-Path $codeDestination $name) }
}

$systemTrees = @('app', 'apps\maestro_android', 'docs', 'services', 'shared', 'sistema', 'tools')
foreach ($relative in $systemTrees) {
    $from = Join-Path $source $relative
    if (Test-Path -LiteralPath $from -PathType Container) {
        Invoke-RobocopyChecked -From $from -To (Join-Path $codeDestination $relative) -Extra @('/XD', '.git', '.venv', 'node_modules', '__pycache__', 'models', 'model', 'checkpoints', 'ckpts', 'weights', 'loras', 'lora_videos', '/XF', '.env', '*.pyc', '*.log', '*.safetensors', '*.ckpt', '*.pt', '*.pth', '*.onnx', '*.gguf', '*.engine', '*.tflite', '*.mlmodel', '*.param')
    }
}

Invoke-RobocopyChecked -From (Join-Path $source 'ferramentas\ComfyUI') -To (Join-Path $codeDestination 'ferramentas\ComfyUI') -Extra @('/XD', '.git', '.venv', 'models', 'model', 'checkpoints', 'ckpts', 'weights', 'loras', 'lora_videos', 'input', 'output', 'temp', '__pycache__', '/XF', '.env', '*.pyc', '*.log', '*.safetensors', '*.ckpt', '*.pt', '*.pth', '*.onnx', '*.gguf', '*.engine', '*.tflite', '*.mlmodel', '*.param')
Invoke-RobocopyChecked -From (Join-Path $source 'ferramentas\video_global_engine') -To (Join-Path $codeDestination 'ferramentas\video_global_engine') -Extra @('/XD', '.git', '.venv', 'node_modules', 'projetos', 'PRONTOS', '__pycache__', 'models', 'model', 'checkpoints', 'ckpts', 'weights', 'loras', 'lora_videos', 'rife-ncnn-vulkan-20221029-windows', 'realesrgan-ncnn-vulkan-20220424-windows', '/XF', '.env', '*.pyc', '*.log', '*.mp4', '*.wav', '*.flac', '*.safetensors', '*.ckpt', '*.pt', '*.pth', '*.onnx', '*.gguf', '*.engine', '*.tflite', '*.mlmodel', '*.param', 'rife-ncnn-vulkan-20221029-windows.zip', 'realesrgan-ncnn-vulkan-20220424-windows.zip')
foreach ($relative in @('ferramentas\audio_neural\HunyuanVideo-Foley', 'ferramentas\audio_neural\hunyuan_gpu', 'ferramentas\audio_neural\video_sound', 'ferramentas\agent_ecosystem')) {
    $from = Join-Path $source $relative
    if (Test-Path -LiteralPath $from -PathType Container) {
        Invoke-RobocopyChecked -From $from -To (Join-Path $codeDestination $relative) -Extra @('/XD', '.git', '.venv', 'node_modules', '__pycache__', 'models', 'model', 'checkpoints', 'ckpts', 'weights', 'loras', 'lora_videos', '/XF', '.env', '*.pyc', '*.log', '*.mp4', '*.wav', '*.flac', '*.safetensors', '*.ckpt', '*.pt', '*.pth', '*.onnx', '*.gguf', '*.engine', '*.tflite', '*.mlmodel', '*.param')
    }
}
Invoke-RobocopyChecked -From (Join-Path $source 'third_party\MiniMax-H3-official') -To (Join-Path $codeDestination 'third_party\MiniMax-H3-official') -Extra @('/XD', '.git', '/XF', '*.pyc')
Invoke-RobocopyChecked -From $agents -To $agentsDestination -Extra @('/XD', '.git', '__pycache__', 'models', 'model', 'checkpoints', 'ckpts', 'weights', 'loras', 'lora_videos', '/XF', '*.pyc', '*.log', '*.safetensors', '*.ckpt', '*.pt', '*.pth', '*.onnx', '*.gguf', '*.engine', '*.tflite', '*.mlmodel', '*.param')

$modelFiles = @(
    'ferramentas\ComfyUI\models\diffusion_models\minimax_h3_fl2va_pruned_int8_convrot.safetensors',
    'ferramentas\ComfyUI\models\text_encoders\qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors',
    'ferramentas\ComfyUI\models\vae\minimax_h3_audio_vae_fp32.safetensors',
    'ferramentas\ComfyUI\models\vae\minimax_h3_video_vae_fp16.safetensors',
    'ferramentas\ComfyUI\models\diffusion_models\qwen_image_2512_fp8_e4m3fn.safetensors',
    'ferramentas\ComfyUI\models\diffusion_models\qwen_image_edit_2511_fp8mixed.safetensors',
    'ferramentas\ComfyUI\models\upscale_models\RealESRGAN_x2plus.pth'
)
if ($IncludeModels) {
    foreach ($relative in $modelFiles) {
        $from = Join-Path $source $relative
        if (-not (Test-Path -LiteralPath $from -PathType Leaf)) {
            throw "Modelo obrigatorio ausente: $from"
        }
        $to = Join-Path $codeDestination $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $to) -Force | Out-Null
        Copy-Item -LiteralPath $from -Destination $to
    }
    $foley = (Resolve-Path -LiteralPath $FoleyModelRoot).Path
    Invoke-RobocopyChecked -From $foley -To $foleyDestination -Extra @('/XF', '*.log')
}

$scripts = @{
    'restore_maestro_minimax_h3.ps1' = 'RESTAURAR_PC_NOVO.ps1'
    'validate_maestro_minimax_h3_backup.ps1' = 'VALIDAR_BACKUP.ps1'
    'validate_maestro_minimax_h3_install.ps1' = 'VALIDAR_INSTALACAO.ps1'
}
foreach ($entry in $scripts.GetEnumerator()) {
    Copy-Item -LiteralPath (Join-Path $source "tools\$($entry.Key)") -Destination (Join-Path $package $entry.Value)
}
Invoke-RobocopyChecked -From (Join-Path $source 'tools\model_installers') -To (Join-Path $package 'INSTALAR_MODELOS') -Extra @('/XD', '__pycache__', '/XF', '*.pyc', '*.log')

python -m pip freeze | Set-Content -LiteralPath (Join-Path $package 'PYTHON_FREEZE.txt') -Encoding utf8
nvidia-smi -q | Set-Content -LiteralPath (Join-Path $package 'NVIDIA_SMI.txt') -Encoding utf8
git -C (Split-Path -Parent $source) status --short | Set-Content -LiteralPath (Join-Path $package 'GIT_STATUS.txt') -Encoding utf8

$manifestFiles = @(
    Get-ChildItem -LiteralPath $payload -Recurse -File
    Get-ChildItem -LiteralPath (Join-Path $package 'INSTALAR_MODELOS') -Recurse -File
)
$manifest = foreach ($file in $manifestFiles) {
    [pscustomobject]@{
        RelativePath = $file.FullName.Substring($package.Length + 1)
        Bytes = $file.Length
        SHA256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
    }
}
$manifest | Export-Csv -LiteralPath (Join-Path $package 'MANIFEST_SHA256.csv') -NoTypeInformation -Encoding utf8
$metadata = [ordered]@{
    schemaVersion = 1
    createdAt = (Get-Date).ToString('o')
    source = $source
    agentsSource = $agents
    package = $package
    includeModels = $IncludeModels
    files = @($manifest).Count
    bytes = (@($manifest) | Measure-Object -Property Bytes -Sum).Sum
    secretsIncluded = $false
    projectsIncluded = $false
    auxiliaryModelWeightsIncluded = $false
    modelInstallerBundleIncluded = $true
    enginePolicy = 'minimax_h3_only'
    workflowVersion = 'maestro-minimax-h3-production@2026-08-16'
}
$metadata | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $package 'SNAPSHOT_METADATA.json') -Encoding utf8

Write-Output $package
