const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const projectRoot = path.resolve(__dirname, '..', 'projetos', 'vejito_super_boo_ltx25_60s');
const batchRoot = path.join(projectRoot, 'keyframes', 'candidates', 'fusion_block');
const projectPath = path.join(projectRoot, 'project_manifest.json');
const productionPath = path.join(projectRoot, 'production_manifest.json');
const queuePath = path.join(projectRoot, 'take_queue.json');
const now = new Date().toISOString();

const definitions = [
  ['anchor_00', 'Goku reveals the Potara pair while Vegeta braces and Super Boo advances.', 'D71FD229A7C692776CB5F32C89E9BCABA07E723BDBAD0C15B0C01A494FA09BE3'],
  ['anchor_01', 'Goku and Vegeta place the matching Potara on opposite ears during Boo attack.', '9AD3D5FA0EA57726ADE4122714A3EE5BF93EF830E819C20DB8CB866BC74D3307'],
  ['anchor_02', 'Potara pull both separate bodies into a white-gold fusion nucleus while Boo misses.', '81D6A535A8B3D9C4FF0D6F9BA1CCAD9E28EACAF15F76AAFEBAD4C23D04A250A9'],
  ['anchor_03', 'Base-form black-haired Vegetto with Potara arrests Boo wrist while both skid.', '57DE199C98E754A6854EC77B83D0F02D2EC87B5EE97A812DBA92B6BD4060628A'],
  ['anchor_04', 'Same Vegetto fully Super Saiyan above Boo with exposed-ear Potara continuity.', 'F26BCD7840B56C592668A19A0D1691D4F296187D36CD72F8C90F0D446D81BD45'],
];

const sha256 = (file) => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex').toUpperCase();
const readJson = (file) => JSON.parse(fs.readFileSync(file, 'utf8'));
const writeJson = (file, value) => fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
const pngSize = (file) => {
  const bytes = fs.readFileSync(file);
  if (bytes.toString('hex', 0, 8) !== '89504e470d0a1a0a') throw new Error(`Not PNG: ${file}`);
  return { width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20) };
};

const candidates = definitions.map(([anchor, description, expected]) => {
  const filename = `${anchor}_candidate_v1.png`;
  const file = path.join(batchRoot, filename);
  if (!fs.existsSync(file)) throw new Error(`Candidate missing: ${file}`);
  const actual = sha256(file);
  if (actual !== expected) throw new Error(`Hash mismatch for ${anchor}: ${actual}`);
  const size = pngSize(file);
  if (size.width !== 1672 || size.height !== 941) throw new Error(`Unexpected dimensions for ${anchor}.`);
  return {
    anchor,
    status: 'PENDING_HUMAN_APPROVAL',
    path: path.relative(projectRoot, file).replaceAll('\\', '/'),
    width: size.width,
    height: size.height,
    sha256: actual,
    prompt_contract: description,
  };
});

const project = readJson(projectPath);
const production = readJson(productionPath);
const queue = readJson(queuePath);
project.updated_at = now;
project.status = 'WAITING_FUSION_BLOCK_HUMAN_APPROVAL';
project.maestro_status = 'WAITING_ANCHORS_00_TO_04_HUMAN_APPROVAL';
project.render_authorized = false;
project.anchor_candidate_batches = project.anchor_candidate_batches || {};
project.anchor_candidate_batches.fusion_and_ssj = {
  status: 'PENDING_HUMAN_APPROVAL',
  created_at: now,
  mode: 'built-in image generation with identity continuity references',
  contact_sheet: 'keyframes/candidates/fusion_block/fusion_block_contact_sheet_v1.jpg',
  candidates,
};

production.updated_at = now;
for (const take of production.takes.filter((item) => ['T01', 'T02', 'T03', 'T04', 'T05'].includes(item.id))) {
  take.qc.status = 'FUSION_BLOCK_CANDIDATES_PENDING_HUMAN_APPROVAL';
  take.qc.human_anchor_approval = 'pending';
  take.generation.render_authorized = false;
}

queue.updated_at = now;
queue.status = 'WAITING_ANCHORS_00_TO_04_HUMAN_APPROVAL';
queue.render_authorized = false;
for (const item of queue.takes.filter((take) => ['T01', 'T02', 'T03', 'T04', 'T05'].includes(take.id))) {
  item.render_authorized = false;
  if (item.id !== 'T06') item.status = 'WAITING_FUSION_BLOCK_ANCHOR_APPROVAL';
}

writeJson(projectPath, project);
writeJson(productionPath, production);
writeJson(queuePath, queue);
writeJson(path.join(batchRoot, 'fusion_anchor_candidates_v1.json'), {
  schema_version: '1.0',
  project_id: project.project_id,
  status: 'PENDING_HUMAN_APPROVAL',
  generation_mode: 'built-in image generation',
  candidates,
});

const report = `# QC - Candidatas de fusao e transformacao\n\n` +
  `Data: ${now}\n\n` +
  `Status: \`PENDING_HUMAN_APPROVAL\`\n\n` +
  candidates.map((item) => `- ${item.anchor}: \`${item.path}\` - ${item.width}x${item.height} - SHA-256 \`${item.sha256}\``).join('\n') +
  `\n\nContact sheet: \`keyframes/candidates/fusion_block/fusion_block_contact_sheet_v1.jpg\`.\n\n` +
  `Nenhuma candidata foi promovida para as ancoras finais e nenhum novo job LTX foi autorizado.\n`;
fs.writeFileSync(path.join(projectRoot, 'qc', 'QC_FUSION_ANCHOR_CANDIDATES_V1.md'), report, 'utf8');

process.stdout.write(`${JSON.stringify({
  ok: true,
  status: project.status,
  candidate_count: candidates.length,
  anchors: candidates.map((item) => item.anchor),
  render_authorized: project.render_authorized,
  audio_status: project.audio.status,
}, null, 2)}\n`);
