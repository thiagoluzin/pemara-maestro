const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const projectRoot = 'E:\\Pemara\\maestro\\pemara\\ferramentas\\video_global_engine\\projetos\\mortal_kombat_irmaos_h3_8x8s';
const queuePath = path.join(projectRoot, 'take_queue.json');
const audioRoot = path.join(projectRoot, 'audio', 'hunyuan_foley_20260814');
const deliveryRoot = path.join(audioRoot, 'deliveries');
const masterPath = path.join(projectRoot, 'deliveries', 'mortal_kombat_irmaos_60s_hunyuan_xxl_ambient_only_fhd.mp4');
const masterQc = path.join(projectRoot, 'deliveries', 'mortal_kombat_irmaos_60s_hunyuan_xxl_ambient_only_fhd_ffprobe.json');
const masterLoudness = path.join(projectRoot, 'deliveries', 'mortal_kombat_irmaos_60s_hunyuan_xxl_ambient_only_fhd_loudness.txt');
const manifestPath = path.join(deliveryRoot, 'hunyuan_xxl_gpu_audio_manifest.csv');

for (const required of [queuePath, masterPath, masterQc, masterLoudness, manifestPath]) {
  if (!fs.existsSync(required)) throw new Error(`Required delivery artifact missing: ${required}`);
}

const queue = JSON.parse(fs.readFileSync(queuePath, 'utf8').replace(/^\uFEFF/, ''));
if (!Array.isArray(queue.takes) || queue.takes.length !== 8) {
  throw new Error('Expected exactly eight takes in take_queue.json.');
}

const generatedAt = new Date().toISOString();
const masterHash = crypto.createHash('sha256').update(fs.readFileSync(masterPath)).digest('hex');
const sourceTake = 'hunyuanvideo_foley_xxl_cuda128_no_offload';
const rightsScope = 'internal_noncommercial_fan_evaluation_only';

for (let index = 0; index < queue.takes.length; index += 1) {
  const takeNumber = index + 1;
  const takeId = String(takeNumber).padStart(2, '0');
  const isPilot = takeNumber === 1;
  const audioFile = isPilot
    ? path.join(audioRoot, 'take01_pilot', 'take01_hunyuan_xxl_ambient_pilot_review.wav')
    : path.join(deliveryRoot, `take_${takeId}_hunyuan_xxl_ambient_gpu_48k_stereo.wav`);
  const reviewVideo = isPilot
    ? path.join(audioRoot, 'take01_pilot', 'take01_hunyuan_xxl_ambient_pilot_review_fhd.mp4')
    : path.join(deliveryRoot, `take_${takeId}_hunyuan_xxl_ambient_gpu_review_fhd.mp4`);

  for (const required of [audioFile, reviewVideo]) {
    if (!fs.existsSync(required)) throw new Error(`Take ${takeId} delivery missing: ${required}`);
  }

  const candidate = {
    id: `hunyuan_xxl_take${takeId}_ambient_gpu`,
    label: `Hunyuan XXL GPU - ambiente sincronizado (Take ${takeId})`,
    file: audioFile,
    status: isPilot ? 'approved_human_listening' : 'candidate_pending_human_listening',
    source_take: sourceTake,
    duration_seconds: 8.0,
    human_listening_required: true,
    automatic_approval: false,
    generated_at: generatedAt,
    technical_qc: manifestPath,
    review_video: reviewVideo,
    engine: 'Tencent HunyuanVideo-Foley XXL',
    device: 'cuda:0 NVIDIA GeForce RTX 5090',
    offload: false,
    sample_rate_hz: 48000,
    channels: 2,
    rights_scope: rightsScope,
  };

  const direction = queue.takes[index].audio_direction || {};
  const previous = Array.isArray(direction.candidate_variants) ? direction.candidate_variants : [];
  direction.human_listening_required = true;
  direction.salvage_candidate = candidate;
  direction.candidate_variants = [
    ...previous.filter((item) => item && item.id !== candidate.id),
    candidate,
  ];
  if (isPilot) {
    direction.human_listening_completed = true;
    direction.foley_qc_status = 'approved_human_listening';
  }
  queue.takes[index].audio_direction = direction;
}

queue.updated_at = generatedAt;
queue.audio_policy = {
  ...(queue.audio_policy || {}),
  current_delivery_mode: 'ambient_only_hunyuan_xxl_gpu_no_music_no_voice',
  neural_engine: 'Tencent HunyuanVideo-Foley XXL',
  neural_device: 'cuda:0 NVIDIA GeForce RTX 5090',
  neural_offload: false,
};
queue.ambient_audio_master = {
  id: 'hunyuan_xxl_gpu_ambient_only_fhd_60s_v1',
  label: 'Filme completo FHD 60s - Hunyuan XXL GPU - somente ambiente e luta',
  file: masterPath,
  status: 'candidate_pending_human_listening',
  duration_seconds: 60.0,
  width: 1920,
  height: 1080,
  fps: 24,
  audio_sample_rate_hz: 48000,
  audio_channels: 2,
  integrated_lufs: -18.3,
  true_peak_dbfs: -2.2,
  music_included: false,
  voice_included: false,
  engine: 'Tencent HunyuanVideo-Foley XXL',
  device: 'cuda:0 NVIDIA GeForce RTX 5090',
  offload: false,
  sha256: masterHash,
  ffprobe: masterQc,
  loudness_report: masterLoudness,
  audio_manifest: manifestPath,
  generated_at: generatedAt,
  rights_scope: rightsScope,
};

fs.writeFileSync(queuePath, `${JSON.stringify(queue, null, 2)}\n`, 'utf8');
console.log(JSON.stringify({ ok: true, queuePath, masterPath, sha256: masterHash }, null, 2));
