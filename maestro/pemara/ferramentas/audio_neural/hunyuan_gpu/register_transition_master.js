const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { spawnSync } = require('child_process');

const projectRoot = 'E:\\Pemara\\maestro\\pemara\\ferramentas\\video_global_engine\\projetos\\mortal_kombat_irmaos_h3_8x8s';
const queuePath = path.join(projectRoot, 'take_queue.json');
const projectManifestPath = path.join(projectRoot, 'project_manifest.json');
const master24 = path.join(projectRoot, 'deliveries', 'mortal_kombat_irmaos_60s_progressao_aprovada_hunyuan_owner_voices_fhd24.mp4');
const master60 = path.join(projectRoot, 'deliveries', 'mortal_kombat_irmaos_60s_progressao_aprovada_hunyuan_owner_voices_fhd60_rife46.mp4');
const probe24Path = path.join(projectRoot, 'deliveries', 'mortal_kombat_irmaos_60s_progressao_aprovada_hunyuan_owner_voices_fhd24.ffprobe.json');
const probe60Path = path.join(projectRoot, 'deliveries', 'mortal_kombat_irmaos_60s_progressao_aprovada_hunyuan_owner_voices_fhd60_rife46.ffprobe.json');
const loudnessPath = path.join(projectRoot, 'deliveries', 'mortal_kombat_irmaos_60s_progressao_aprovada_hunyuan_owner_voices_fhd24.loudness.txt');

for (const required of [queuePath, projectManifestPath, master24, master60, loudnessPath]) {
  if (!fs.existsSync(required)) throw new Error(`Required final artifact missing: ${required}`);
}

function sha256(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function probe(file) {
  const result = spawnSync('ffprobe', [
    '-v', 'error', '-count_frames', '-show_format', '-show_streams', '-of', 'json', file,
  ], { encoding: 'utf8' });
  if (result.status !== 0) throw new Error(`ffprobe failed for ${file}: ${result.stderr}`);
  return JSON.parse(result.stdout);
}

const probe24 = probe(master24);
const probe60 = probe(master60);
fs.writeFileSync(probe24Path, `${JSON.stringify(probe24, null, 2)}\n`, 'utf8');
fs.writeFileSync(probe60Path, `${JSON.stringify(probe60, null, 2)}\n`, 'utf8');

const video24 = probe24.streams.find((stream) => stream.codec_type === 'video');
const audio24 = probe24.streams.find((stream) => stream.codec_type === 'audio');
const video60 = probe60.streams.find((stream) => stream.codec_type === 'video');
const audio60 = probe60.streams.find((stream) => stream.codec_type === 'audio');
if (!video24 || !audio24 || !video60 || !audio60) throw new Error('Final video/audio streams are incomplete.');
if (Number(video24.nb_read_frames) !== 1440 || Number(video60.nb_read_frames) !== 3600) {
  throw new Error('Final frame contract mismatch.');
}

const generatedAt = new Date().toISOString();
const hash24 = sha256(master24);
const hash60 = sha256(master60);
const rightsScope = 'internal_noncommercial_fan_evaluation_only';
const audioDecodedSha256 = '3321fecc635bf920fa72f322232c2afa13392339cfd7ec0451a67edbb5ebc560';

const variants = [
  {
    id: 'fhd24_review',
    label: 'Filme completo FHD 24 fps - progressao aprovada, Foley neural e vozes do proprietario',
    file: master24,
    duration_seconds: 60.0,
    width: 1920,
    height: 1080,
    fps: 24,
    frames: 1440,
    sha256: hash24,
    role: 'mobile_review_proxy',
  },
  {
    id: 'fhd60_rife46_final',
    label: 'Filme completo FHD 60 fps RIFE 4.6 - entrega final',
    file: master60,
    duration_seconds: 60.0,
    width: 1920,
    height: 1080,
    fps: 60,
    frames: 3600,
    sha256: hash60,
    role: 'master_download',
  },
];

const queue = JSON.parse(fs.readFileSync(queuePath, 'utf8').replace(/^\uFEFF/, ''));
queue.updated_at = generatedAt;
queue.status = 'FINAL_MASTER_READY';
queue.audio_policy = {
  ...(queue.audio_policy || {}),
  current_delivery_mode: 'hunyuan_xxl_environment_and_fight_plus_owner_voices_no_music',
  neural_engine: 'Tencent HunyuanVideo-Foley XXL',
  neural_device: 'cuda:0 NVIDIA GeForce RTX 5090',
  neural_offload: false,
  procedural_python_audio: 'prohibited',
};
queue.final_master_history = [...(queue.final_master_history || []), ...(queue.final_master ? [queue.final_master] : [])];
queue.final_master = {
  id: 'mk_brothers_progressao_aprovada_fhd60_rife46',
  label: 'Filme completo 60s - progressao aprovada, Foley XXL, vozes originais e RIFE 60 fps',
  file: master60,
  review_file: master24,
  status: 'final_delivery_ready',
  duration_seconds: 60.0,
  width: 1920,
  height: 1080,
  fps: 60,
  frames: 3600,
  audio_sample_rate_hz: 48000,
  audio_channels: 2,
  integrated_lufs: -16.9,
  true_peak_dbfs: -1.0,
  audio_decoded_sha256: audioDecodedSha256,
  music_included: false,
  voice_included: true,
  voice_source: 'owner_supplied_take_07_take_08',
  transition_count: 7,
  foley_engine: 'Tencent HunyuanVideo-Foley XXL',
  foley_device: 'cuda:0 NVIDIA GeForce RTX 5090',
  interpolation_engine: 'RIFE v4.6 ncnn Vulkan',
  interpolation_device: 'NVIDIA GeForce RTX 5090 Vulkan device 0',
  sha256: hash60,
  review_sha256: hash24,
  ffprobe: probe60Path,
  review_ffprobe: probe24Path,
  loudness_report: loudnessPath,
  variants,
  generated_at: generatedAt,
  rights_scope: rightsScope,
};
queue.ambient_audio_master = { ...queue.final_master, legacy_field_alias: true };
queue.delivery_variants = variants;
fs.writeFileSync(queuePath, `${JSON.stringify(queue, null, 2)}\n`, 'utf8');

const project = JSON.parse(fs.readFileSync(projectManifestPath, 'utf8').replace(/^\uFEFF/, ''));
project.updated_at = generatedAt;
project.status = 'FINAL_MASTER_READY';
project.maestro_status = 'FINAL_MASTER_READY';
project.render_authorized = true;
project.render_authority = 'owner_authorized_in_codex_2026-08-14';
project.fps_preview = 24;
project.fps_final = 60;
project.audio = {
  ...(project.audio || {}),
  music_provider: 'none; owner requested environment, fight Foley and supplied voices only',
  foley_provider: 'Tencent HunyuanVideo-Foley XXL local neural runtime on cuda:0 RTX 5090 without offload',
  foley_candidate_status: 'all_eight_takes_and_seven_transitions_generated_and_assembled',
  voice_provider: 'owner_supplied_finish_him_fatality_flawless_victory_mixed_into_take_07_08',
  voice_status: 'included_in_final_master_audio_bitstream',
  procedural_python_audio: 'prohibited',
};
project.final_output = {
  file: path.relative(projectRoot, master60).replace(/\\/g, '/'),
  review_file: path.relative(projectRoot, master24).replace(/\\/g, '/'),
  duration_seconds: 60.0,
  width: 1920,
  height: 1080,
  fps: 60,
  frames: 3600,
  video_codec: 'h264 RIFE 4.6 NVENC',
  audio_codec: 'aac stereo 48000 Hz 320 kbps',
  integrated_lufs: -16.9,
  true_peak_dbfs: -1.0,
  audio_decoded_sha256: audioDecodedSha256,
  music_included: false,
  voice_included: true,
  transition_count: 7,
  neural_audio_engine: 'Tencent HunyuanVideo-Foley XXL',
  neural_audio_device: 'cuda:0 NVIDIA GeForce RTX 5090',
  neural_audio_offload: false,
  interpolation_engine: 'RIFE v4.6 ncnn Vulkan on NVIDIA GeForce RTX 5090 device 0',
  sha256: hash60,
  review_sha256: hash24,
  qc_status: 'technical_pass',
  variants,
};
fs.writeFileSync(projectManifestPath, `${JSON.stringify(project, null, 2)}\n`, 'utf8');

console.log(JSON.stringify({
  ok: true,
  project: project.project_id,
  final_master: master60,
  review_proxy: master24,
  sha256: hash60,
  audio_decoded_sha256: audioDecodedSha256,
}, null, 2));
