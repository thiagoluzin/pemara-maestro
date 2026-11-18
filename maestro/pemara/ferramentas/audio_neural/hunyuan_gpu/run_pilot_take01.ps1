$ErrorActionPreference = 'Stop'

$modelRoot = 'G:\Pemara_AI_Models\HunyuanVideo-Foley'
$projectRoot = 'E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\mortal_kombat_irmaos_h3_8x8s'
$videoRoot = Join-Path $projectRoot 'audio\hunyuan_foley_20260814\inputs'
$outputRoot = Join-Path $projectRoot 'audio\hunyuan_foley_20260814\take01_pilot'
$videoName = 'take01_hunyuan_input_512x288_24fps.mp4'
$prompt = 'Ultra-realistic live-action stone arena ambience synchronized precisely to visible movement: strong wind, large fire braziers, heavy hanging chains, distant restless crowd, sand under boots, armor plates, leather, cloth, controlled breathing and two masked fighters approaching. Natural cinematic location sound and physical Foley only.'
$negative = 'music, soundtrack, melody, rhythm, drums, vocals, speech, dialogue, announcer, chant, synthesizer, chiptune, retro game sound, arcade bleeps, cartoon, laser, gunfire'

New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null

docker run --rm --gpus all `
  --env HF_HUB_OFFLINE=1 `
  --env TRANSFORMERS_OFFLINE=1 `
  --mount "type=bind,source=$modelRoot,target=/models,readonly" `
  --mount "type=bind,source=$videoRoot,target=/input,readonly" `
  --mount "type=bind,source=$outputRoot,target=/output" `
  pemara/hunyuanvideo-foley:cuda128 `
  --model_path /models `
  --model_size xxl `
  --device cuda `
  --gpu_id 0 `
  --single_video "/input/$videoName" `
  --single_prompt $prompt `
  --neg_prompt $negative `
  --output_dir /output `
  --audio_length 8 `
  --num_inference_steps 50
