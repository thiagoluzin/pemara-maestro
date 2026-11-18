const fs = require('fs');
const path = require('path');

const root = 'E:\\Pemara\\maestro\\pemara\\ferramentas\\video_global_engine\\projetos\\vejito_super_boo_ltx25_60s';
const timestamp = new Date().toISOString();

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
project.character_continuity = {
  potara: 'Vegetto wears both gold Potara earrings after fusion; every unobscured visible ear must show its earring, and both must be readable whenever both ears are visible.',
  base_form: 'T03 and the opening of T04 use black-haired base-form Vegetto.',
  transformation: 'T04 shows the full live-action Super Saiyan transformation during continuous combat.',
  super_saiyan: 'From the end of T04 through T12, Vegetto keeps gold upright hair, blue-green eyes, gold aura accents and both Potara earrings.',
  automatic_reject: ['missing Potara on an unobscured visible ear after fusion', 'black hair after T04', 'instant unexplained Super Saiyan state', 'anime or game-render appearance'],
};

production.updated_at = timestamp;
production.character_continuity = project.character_continuity;
const t03 = production.takes.find((take) => take.id === 'T03');
const t04 = production.takes.find((take) => take.id === 'T04');
if (!t03 || !t04) throw new Error('T03/T04 missing');

t03.shot_contract.story_change += ' Vegetto emerges in base form with black hair and two visible gold Potara earrings.';
t03.generation.prompt += ' Vegetto must emerge in base form with black hair and two clearly visible gold Potara earrings; never omit either earring.';

t04.title = 'Vegetto se transforma em Super Saiyajin durante a luta';
t04.shot_contract.story_purpose = 'Mostrar a transformacao completa em cena, nascida da pressao de Boo e sem interromper a luta para uma pose cerimonial.';
t04.shot_contract.dramatic_question = 'Vegetto consegue transformar a pressao de Boo em uma explosao Super Saiyajin?';
t04.shot_contract.motion_beats = {
  start: 'Vegetto em forma base, cabelo preto e dois brincos Potara dourados visiveis, ainda preso na acao herdada.',
  middle: 'Boo envolve Vegetto; olhos clareiam, cabelo se ergue e muda progressivamente para dourado; aura fisica rompe poeira e contato.',
  end: 'Vegetto Super Saiyajin completo, cabelo dourado, olhos azul-esverdeados e dois Potara visiveis, surge acima de Boo.',
};
t04.shot_contract.story_change = `${t04.shot_contract.motion_beats.start} -> ${t04.shot_contract.motion_beats.end}`;
t04.shot_contract.reaction = 'Boo perde a pegada, protege o rosto da aura e reage tarde ao aumento de velocidade.';
t04.shot_contract.cut_motivation = 'Cortar quando Boo reconhece Vegetto Super Saiyajin acima.';
t04.generation.prompt = [
  'Animate between the exact approved first and last keyframes as one continuous photorealistic live-action combat action.',
  'Start with Vegetto in base form: black hair and two visible gold Potara earrings.',
  'Super Boo wraps and pressures him without pausing. While still trapped and moving, Vegetto transforms progressively on camera: eyes brighten blue-green, black hair rises and turns gold strand by strand, realistic gold energy distorts dust and cloth, and the aura physically breaks the hold.',
  'End with fully transformed Super Saiyan Vegetto above Boo: upright gold hair, blue-green eyes, both Potara earrings still clearly visible, exact same realistic adult human face and practical costume.',
  'Boo shields his face and loses the grip as a direct reaction.',
  'Premium live-action feature film, realistic skin and fabrics, physically based energy VFX, physical camera translation and real depth.',
  'Forbidden: missing earring, only one Potara, instant unexplained transformation, hair flicker back to black, anime, animation, cel shading, 3D render, robotic pose, turn-based exchange, pose reset, extra character.',
].join(' ');

for (const take of production.takes) {
  const number = Number(take.id.slice(1));
  if (number >= 5) {
    take.generation.prompt += ' Preserve Super Saiyan Vegetto for the entire take: upright gold hair, blue-green eyes, realistic gold aura accents and two visible gold Potara earrings. Never revert to black hair.';
    take.shot_contract.forbidden = [...new Set([...(take.shot_contract.forbidden || []), 'missing Potara earrings', 'black-hair reversion after T04'])];
  }
  take.qc.status = 'WAITING_PHOTOREAL_POTARA_SSJ_ANCHORS';
  take.qc.human_anchor_approval = 'pending';
}

queue.updated_at = timestamp;
queue.status = 'WAITING_PHOTOREAL_POTARA_SSJ_ANCHORS';
for (const take of queue.takes) take.status = 'WAITING_APPROVED_PHOTOREAL_POTARA_SSJ_ANCHORS';

writeJson('project_manifest.json', project);
writeJson('production_manifest.json', production);
writeJson('take_queue.json', queue);

const qc = `# QC - Potara e transformacao Super Saiyajin\n\n` +
  `Data: ${timestamp}\n\n` +
  `As candidatas fotorealistas T06 v1 foram reprovadas antes do LTX porque Vegetto apareceu sem os dois brincos Potara e em forma base.\n\n` +
  `Correcao de continuidade:\n` +
  `- T03: Vegetto base com dois Potara visiveis.\n` +
  `- T04: transformacao completa em Super Saiyajin durante combate continuo.\n` +
  `- T05-T12: Super Saiyajin constante, cabelo dourado, olhos azul-esverdeados e dois Potara.\n\n` +
  `Nenhum job LTX foi executado e nenhuma ancora final foi aprovada.\n`;
fs.writeFileSync(path.join(root, 'qc', 'QC_REJEICAO_POTARA_SSJ.md'), qc, 'utf8');

console.log(JSON.stringify({
  ok: true,
  project_id: project.project_id,
  transformation_take: 'T04',
  super_saiyan_from: 'T04 end',
  potara_required_from: 'T03',
  render_authorized: false,
}, null, 2));
