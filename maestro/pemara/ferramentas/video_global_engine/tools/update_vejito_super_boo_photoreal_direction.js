const fs = require('fs');
const path = require('path');

const root = 'E:\\Pemara\\maestro\\pemara\\ferramentas\\video_global_engine\\projetos\\vejito_super_boo_ltx25_60s';
const timestamp = new Date().toISOString();
const style = [
  'photorealistic live-action feature film with real human performers and a physically convincing pink humanoid',
  'natural skin pores, sweat, fabric, practical costume texture, cinematic lenses and realistic motion blur',
  'large-scale practical destruction enhanced by premium physically based visual effects',
  'asymmetric timing, interrupted attacks, weighted contact and immediate human reactions',
  'cinematic physical camera translation with foreground, midground and background parallax; never animation or a game render',
].join(', ');
const styleReject = [
  'anime',
  'animation',
  'cel shading',
  'illustration',
  'manga',
  'cartoon',
  '3D render',
  'game cinematic',
  'plastic skin',
];

function readJson(name) {
  return JSON.parse(fs.readFileSync(path.join(root, name), 'utf8').replace(/^\uFEFF/, ''));
}
function writeJson(name, value) {
  fs.writeFileSync(path.join(root, name), `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

const project = readJson('project_manifest.json');
const production = readJson('production_manifest.json');
const queue = readJson('take_queue.json');

project.updated_at = timestamp;
project.visual_identity = {
  medium: 'photorealistic live-action feature film',
  humans: 'Goku, Vegeta and Vegetto portrayed as believable adult human performers',
  humanoid: 'Super Boo portrayed as a physically convincing pink humanoid with realistic skin and costume materials',
  vfx: 'premium physically based energy, destruction, debris, atmospherics and camera effects',
  forbidden: styleReject,
};
project.status = 'PREPRODUCTION_PHOTOREAL_ANCHORS_REQUIRED';
project.maestro_status = 'WAITING_PHOTOREAL_ANCHOR_GENERATION_AND_HUMAN_APPROVAL';

production.updated_at = timestamp;
production.global_style = style;
production.global_forbidden = [...new Set([...(production.global_forbidden || []), ...styleReject.map((item) => `no ${item}`)])];
for (const take of production.takes) {
  take.generation.prompt = take.generation.prompt.replace(
    /Visual language: .*?\. Camera:/,
    `Visual language: ${style}. Camera:`,
  );
  take.generation.negative_prompt = [...new Set([
    ...String(take.generation.negative_prompt || '').split(',').map((item) => item.trim()).filter(Boolean),
    ...styleReject,
  ])].join(', ');
  take.qc.status = 'WAITING_PHOTOREAL_ANCHORS';
  take.qc.human_anchor_approval = 'pending';
}

queue.updated_at = timestamp;
queue.status = 'WAITING_PHOTOREAL_ANCHORS';
for (const take of queue.takes) take.status = 'WAITING_APPROVED_PHOTOREAL_ANCHORS';

writeJson('project_manifest.json', project);
writeJson('production_manifest.json', production);
writeJson('take_queue.json', queue);

const qc = `# QC - correcao de linguagem visual\n\n` +
  `Data: ${timestamp}\n\n` +
  `As duas primeiras candidatas conceituais do T06 foram reprovadas antes de entrar no projeto porque usavam animacao estilizada. ` +
  `A direcao correta e filme live-action fotorealista: humanos reais para Goku, Vegeta e Vegetto; humanoide fisico para Super Boo; VFX cinematografico fisicamente plausivel.\n\n` +
  `Nenhum job LTX foi executado e nenhuma ancora final foi aprovada.\n`;
fs.writeFileSync(path.join(root, 'qc', 'QC_REJEICAO_ESTILO_ANIMACAO.md'), qc, 'utf8');

console.log(JSON.stringify({
  ok: true,
  project_id: project.project_id,
  visual_medium: project.visual_identity.medium,
  rejected_before_ltx: 2,
  render_authorized: project.render_authorized,
  queue_status: queue.status,
}, null, 2));
