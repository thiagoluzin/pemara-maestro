const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const projectRoot = path.resolve(__dirname, '..', 'projetos', 'vejito_super_boo_ltx25_60s');
const projectPath = path.join(projectRoot, 'project_manifest.json');
const productionPath = path.join(projectRoot, 'production_manifest.json');
const queuePath = path.join(projectRoot, 'take_queue.json');
const now = new Date().toISOString();

const readJson = (file) => JSON.parse(fs.readFileSync(file, 'utf8'));
const writeJson = (file, data) => fs.writeFileSync(file, `${JSON.stringify(data, null, 2)}\n`, 'utf8');
const sha256 = (file) => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex').toUpperCase();

const project = readJson(projectPath);
const production = readJson(productionPath);
const queue = readJson(queuePath);

const startCandidate = path.join(projectRoot, project.pilot_anchor_candidates.start.path);
const endCandidate = path.join(projectRoot, project.pilot_anchor_candidates.end.path);
const startAnchor = path.join(projectRoot, 'keyframes', 'anchor_05.png');
const endAnchor = path.join(projectRoot, 'keyframes', 'anchor_06.png');

for (const [label, file, expected] of [
  ['start', startCandidate, project.pilot_anchor_candidates.start.sha256],
  ['end', endCandidate, project.pilot_anchor_candidates.end.sha256],
]) {
  if (!fs.existsSync(file)) throw new Error(`Missing ${label} candidate: ${file}`);
  const actual = sha256(file);
  if (actual !== expected) throw new Error(`${label} candidate hash mismatch: ${actual}`);
}

fs.copyFileSync(startCandidate, startAnchor);
fs.copyFileSync(endCandidate, endAnchor);

project.updated_at = now;
project.status = 'PILOT_T06_ANCHORS_APPROVED';
project.maestro_status = 'READY_FOR_T06_LTX25_PILOT';
project.render_authorized = true;
project.render_authority = 'owner approval in Codex task';
project.render_scope = 'T06_ONLY';
project.pilot_anchor_candidates.status = 'APPROVED_AND_PROMOTED_FOR_T06_ONLY';
project.pilot_anchor_candidates.approved_at = now;
project.pilot_anchor_candidates.not_registered_as_final_anchors = false;
project.pilot_anchor_candidates.promoted = {
  start: 'keyframes/anchor_05.png',
  end: 'keyframes/anchor_06.png',
};

production.updated_at = now;
for (const take of production.takes) {
  if (take.id !== 'T06') continue;
  take.generation.status = 'READY_FOR_LTX25_PILOT';
  take.generation.render_authorized = true;
  take.shot_contract.keyframes.approved = true;
  take.qc.status = 'ANCHORS_APPROVED_WAITING_LTX25_PILOT';
  take.qc.human_anchor_approval = 'approved';
  take.qc.human_anchor_approved_at = now;
}

queue.updated_at = now;
queue.status = 'READY_FOR_T06_LTX25_PILOT';
queue.render_authorized = true;
for (const take of queue.takes) {
  const isPilot = take.id === 'T06';
  take.render_authorized = isPilot;
  if (isPilot) {
    take.status = 'READY_FOR_LTX25_PILOT';
    take.qc_status = 'anchors_approved';
  }
}

writeJson(projectPath, project);
writeJson(productionPath, production);
writeJson(queuePath, queue);

const approvalDoc = `# Aprovacao humana das ancoras T06\n\n` +
  `Data: ${now}\n\n` +
  `O proprietario aprovou as duas candidatas fotorealistas do piloto T06.\n\n` +
  `- Inicio promovido: \`keyframes/anchor_05.png\`\n` +
  `  - SHA-256 \`${sha256(startAnchor)}\`\n` +
  `- Fim promovido: \`keyframes/anchor_06.png\`\n` +
  `  - SHA-256 \`${sha256(endAnchor)}\`\n\n` +
  `Escopo autorizado: somente T06 no LTX-2.5. Os demais takes e o audio continuam bloqueados.\n`;
fs.writeFileSync(path.join(projectRoot, 'qc', 'QC_APROVACAO_ANCORAS_T06.md'), approvalDoc, 'utf8');

process.stdout.write(`${JSON.stringify({
  ok: true,
  project_id: project.project_id,
  scope: project.render_scope,
  start_anchor_sha256: sha256(startAnchor),
  end_anchor_sha256: sha256(endAnchor),
  queue_status: queue.status,
  audio_status: project.audio.status,
}, null, 2)}\n`);
