const fs = require('fs');
const path = require('path');

const sourceRoot = 'E:\\Pemara\\maestro\\pemara\\ferramentas\\video_global_engine\\projetos\\mortal_kombat_irmaos_transicoes_h3';
const targetRoot = 'E:\\Pemara\\maestro\\pemara\\ferramentas\\video_global_engine\\projetos\\mortal_kombat_irmaos_transicoes_progressao_v2';
const projectId = 'mortal_kombat_irmaos_transicoes_progressao_v2';

if (fs.existsSync(path.join(targetRoot, 'project_manifest.json')) || fs.existsSync(path.join(targetRoot, 'production_manifest.json'))) {
  throw new Error(`Target already contains registered manifests: ${targetRoot}`);
}
for (const dir of ['keyframes', path.join('takes', 'maestro_generated'), 'qc', 'audio', 'editorial_2s']) {
  fs.mkdirSync(path.join(targetRoot, dir), { recursive: true });
}
for (const file of fs.readdirSync(path.join(sourceRoot, 'keyframes'))) {
  if (file.toLowerCase().endsWith('.png')) {
    fs.copyFileSync(path.join(sourceRoot, 'keyframes', file), path.join(targetRoot, 'keyframes', file));
  }
}

const direction = {
  B01_02: {
    purpose: 'Continuar a aproximacao ja iniciada ate o primeiro choque, sem desacelerar ou recomecar a corrida.',
    storyChange: 'Os irmaos passam de trajetorias convergentes distantes para contato firme de antebracos no centro.',
    action: 'Both fighters preserve their existing forward velocity, accelerate once, plant once and collide forearms without any retreat or second approach.',
    camera: 'A straight low forward dolly aligned with the fighters converging movement; no orbit and no camera reversal.',
    middle: 'distance closes continuously; boots keep forward traction; the single forearm collision absorbs both momentum vectors',
    reaction: 'Both torsos compress into the collision and remain engaged; neither fighter bounces back into a starting stance.',
    prompt: `SINGLE MONOTONIC CONTINUATION between the exact supplied first and last frames. Preserve the exact blue masked cryomancer, black hooded shadow revenant, one emperor, one throne, arena axis, costumes and proportions. At frame one both fighters are already advancing toward each other. Keep both momentum vectors forward for the entire shot: they accelerate once, close distance continuously, plant one foot each and collide their armored forearms in the exact supplied end pose. The collision is the only combat event. Camera makes one straight low physical dolly in the same direction as the convergence; a foreground chain may cross only briefly without hiding either body. Timeline: 0-20% inherit the existing run with no new wind-up; 20-80% continuously reduce distance; 80-100% absorb the single collision and hold the matched end state. FORBIDDEN: backward step, deceleration to idle, circling, renewed sprint, pose reset, guard reset, repeated collision, flip, roll, spin, camera reversal, hidden pose jump, teleport, mask change, extra fighter, duplicated emperor.`
  },
  B02_03: {
    purpose: 'Transformar o choque anterior em deslocamento e separacao, sem repetir o bloqueio nem recomecar um golpe.',
    storyChange: 'O contato travado vira uma unica pressao de gelo que desloca Noob para tras e separa os irmaos.',
    action: 'Sub-Zero pushes through the already established forearm contact while frost spreads forward; Noob yields only along the received impact vector.',
    camera: 'One short lateral truck that stays on the same side of the action line and reveals separation without a full lens occlusion.',
    middle: 'the existing locked arms continue forward, frost travels from the same contact point and Noob is displaced along one consistent impact vector',
    reaction: 'Noob recoils continuously from the existing pressure while Sub-Zero remains committed and never retracts to strike again.',
    prompt: `SINGLE MONOTONIC FOLLOW-THROUGH between the exact supplied first and last frames. Preserve the exact two masked brothers, one emperor, one throne, arena axis, armor and proportions. Begin with the forearms already locked from the previous collision. Sub-Zero does not retract, wind up or punch again: he pushes through that same contact once as frost grows forward from the existing point of pressure. Noob yields and travels backward only along that received impact vector, his cloak trailing behind the displacement; he never charges back. End in the exact supplied separated powered stance. Camera performs one short lateral physical truck on the same side of the action line; keep both bodies visible and do not use full-frame cloak occlusion. Timeline: 0-20% inherit contact pressure; 20-80% one continuous frost-assisted displacement; 80-100% separate and settle directly into the end frame. FORBIDDEN: return to guard, arm retraction, second punch, countercharge, forward-back-forward motion, pose reset, orbit across the axis, full lens blackout, hidden geometry swap, flip, roll, spin, teleport, duplicated emperor, identity drift.`
  },
  B03_04: {
    purpose: 'Continuar a esquiva baixa de Noob para uma entrada corporal unica, sem recuar antes do clinche.',
    storyChange: 'Noob sai da linha do gelo, avanca pela lateral e fecha um unico clinche com Sub-Zero.',
    action: 'Noob continues the already established lateral evade, plants once and converts the same motion into one forward body clinch.',
    camera: 'One low side track parallel to Noob movement, rising only after the clinch is established; never moving backward.',
    middle: 'Noob clears the ice ridge without stopping, keeps the same lateral-forward vector and closes the remaining distance into the clinch',
    reaction: 'Sub-Zero braces once against the incoming body mass; neither brother disengages or restarts.',
    prompt: `SINGLE MONOTONIC ENTRY between the exact supplied first and last frames. Preserve the exact masked brothers, arena, one emperor, one throne, costumes and proportions. Noob is already evading the ice ridge at frame one. Continue that same lateral-forward vector without pause: he clears the ridge, plants one outside foot and converts the existing momentum directly into one controlled body clinch with Sub-Zero. Sub-Zero braces once and receives the mass; he does not launch another ice wave or step away. Camera performs one low side track parallel to Noob and rises only after physical contact is established. Timeline: 0-20% continue the existing evade; 20-80% uninterrupted distance closure; 80-100% establish and hold the exact supplied grapple. FORBIDDEN: backward step, crouch-stand-crouch cycle, renewed charge, repeated grapple, disengagement, stance reset, sliding feet, somersault, roll, spin, camera reversal, teleport, limb duplication, mask change, identity drift.`
  },
  B04_05: {
    purpose: 'Dar consequencia direta ao golpe ja estendido de Sub-Zero e permitir uma unica reversao fisica de vantagem por Noob.',
    storyChange: 'O soco estendido e desviado para fora da linha e Noob usa o mesmo contato para assumir vantagem.',
    action: 'The already extended blue punch continues through its follow-through; Noob redirects that same arm once and drives one grounded shoulder-elbow counter.',
    camera: 'One tight side truck following the existing punch direction; no orbit, whip pan or occlusion that hides the bodies.',
    middle: 'Noob maintains contact with the extended arm, guides it past his shoulder and pivots once into a grounded counter without resetting either fighter',
    reaction: 'Sub-Zero recoils only after the counter contact and only along its impact vector; Noob remains planted in advantage.',
    prompt: `STRICT CONTINUATION OF THE ALREADY EXTENDED SUB-ZERO STRIKE between the exact supplied first and last frames. Preserve both exact masked brothers, one emperor, one throne, armor, arena axis and proportions. The blue arm is already committed at frame one. NEVER retract it and NEVER repeat the punch. Noob keeps physical contact with that same extended arm, guides its follow-through past his shoulder, plants one foot, pivots outside once and drives one short grounded shoulder-elbow counter through the open guard. Only after that contact may Sub-Zero recoil, and only along the counter impact vector. End directly in the exact supplied Noob-advantage pose. Camera makes one tight side truck following the original punch direction with both torsos visible. Timeline: 0-25% continue the existing punch follow-through; 25-75% redirect the same arm and pivot once; 75-100% one counter impact and resulting recoil. FORBIDDEN: arm retraction, new wind-up, second blue strike, fake, backstep, forward-back-forward motion, guard reset, idle stance, acrobatics, flip, roll, spin, full cloak blackout, hidden pose swap, camera reversal, teleport, identity drift.`
  },
  B05_06: {
    purpose: 'Converter a queda existente de Sub-Zero em recuperacao curta e contra-ataque unico, sem cambalhota ou segundo ciclo.',
    storyChange: 'Sub-Zero termina a queda, planta o joelho e transforma a mesma inercia em uma unica interceptacao gelada.',
    action: 'Sub-Zero completes the existing fall with a shoulder skid, plants one knee and one boot, rises forward once and intercepts Noob once.',
    camera: 'One low forward push aligned with Sub-Zero recovery; the camera rises with him and never pulls back.',
    middle: 'the fall loses energy into a short shoulder skid, then one knee and boot plant convert the remaining momentum forward into the intercept',
    reaction: 'Noob continues his incoming attack until the single icy palm contact stops him; neither fighter starts a second exchange.',
    prompt: `SINGLE MONOTONIC RECOVERY AND INTERCEPT between the exact supplied first and last frames. Preserve both exact masked brothers, one emperor, one throne, arena, costumes and proportions. Sub-Zero is already falling at frame one. Complete only that fall with a short weighted shoulder skid; NO full body roll and NO somersault. He plants one knee and one boot, converts the remaining momentum forward, rises once and intercepts Noob incoming arm with one cold palm. Noob advances only until that single contact stops him; he never withdraws and attacks again. Camera makes one low forward push and rises with Sub-Zero, never pulling backward. Timeline: 0-25% finish the existing fall; 25-60% one knee-and-boot plant; 60-100% one forward rise and one icy intercept into the exact end frame. FORBIDDEN: cambalhota, complete roll, flip, spin, bounce, second fall, standing reset, retreat, repeated attack, guard reset, camera reversal, teleport, rubber limbs, identity drift.`
  },
  B06_07: {
    purpose: 'Levar o golpe gelado ja conectado ate o colapso de Noob, mantendo o imperador sentado para o Take 07 executar sua propria levantada.',
    storyChange: 'A pressao gelada termina de vencer Noob, que afunda em um joelho; Sub-Zero mantem o follow-through e o imperador ainda nao se levanta.',
    action: 'Sub-Zero keeps the existing icy palm committed while frost spreads forward and Noob knees buckle into one continuous kneel.',
    camera: 'One restrained forward crane from the impact toward the kneeling result; no retreat and no throne action.',
    middle: 'ice spreads only forward from the existing contact while Noob loses height continuously until one knee reaches the floor',
    reaction: 'Sub-Zero holds the completed follow-through; the emperor remains seated and merely leans forward, reserving his rise for Take 07.',
    prompt: `SINGLE MONOTONIC CONSEQUENCE OF THE ALREADY CONNECTED ICE STRIKE between the exact supplied first and last frames. Preserve the exact blue masked cryomancer, black hooded revenant, one SEATED emperor, one throne, arena and proportions. Sub-Zero palm is already committed at frame one. NEVER retract it and NEVER strike again. Frost spreads only forward from that existing contact across Noob armor; Noob continuously loses height, his knees buckle and one knee reaches the floor in the exact supplied end state. Sub-Zero holds the completed follow-through instead of returning to guard. The emperor MUST REMAIN SEATED for the entire bridge; he may only lean forward slightly because his rise belongs to Take 07. Camera performs one restrained forward crane from impact to kneeling consequence, never pulling back. Timeline: 0-25% inherit the connected strike; 25-80% frost advances and Noob descends continuously; 80-100% kneel and held follow-through. FORBIDDEN: emperor standing, emperor sitting back down, blue arm retraction, second strike, release-and-regrip, Noob rising before kneeling, bounce, roll, flip, spin, guard reset, camera reversal, teleport, new person, mask change, identity drift.`
  },
  B07_08: {
    purpose: 'Continuar a aproximacao final de Sub-Zero ate a agarrada, sem recuo, finta, golpe antecipado ou reabertura das maos.',
    storyChange: 'Sub-Zero avanca uma unica passada e transforma suas maos prontas na agarrada final; Noob permanece atordoado.',
    action: 'Sub-Zero takes exactly one final forward step and moves both hands directly into the established two-hand grip while Noob remains stunned.',
    camera: 'One short forward arc no greater than thirty degrees, always advancing with Sub-Zero and never reversing.',
    middle: 'the distance closes continuously during one grounded step; both hands travel directly from ready position to the target without feinting',
    reaction: 'Noob remains stunned and yields only to the established grip; he does not attack, retreat or stand independently.',
    prompt: `SINGLE MONOTONIC APPROACH TO THE FINAL GRIP between the exact supplied first and last frames. Preserve the exact blue masked cryomancer, black hooded revenant, one emperor, one throne, arena, masks, armor and proportions. Sub-Zero is already committed forward. He takes exactly ONE grounded forward step and both hands travel directly from their ready position to establish the exact supplied two-hand grip. His hands never close, reopen or feint; he never retreats and does not strike yet. Noob remains stunned, does not attack, does not step back and moves only as the grip takes his weight. Camera makes one short advancing arc under thirty degrees, always moving forward with Sub-Zero. Timeline: 0-25% inherit forward commitment; 25-75% one uninterrupted step and direct hand travel; 75-100% establish and hold the grip with no release. FORBIDDEN: backward step, fist close-open cycle, feint, punch, premature fatality, grip-release-regrip, Noob counterattack, independent rise, guard reset, roll, flip, spin, camera reversal, teleport, face exposure, extra fingers, identity drift.`
  },
};

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
}

function rewritePaths(value) {
  if (Array.isArray(value)) return value.map(rewritePaths);
  if (value && typeof value === 'object') {
    for (const key of Object.keys(value)) value[key] = rewritePaths(value[key]);
    return value;
  }
  return typeof value === 'string' ? value.split(sourceRoot).join(targetRoot) : value;
}

function updateTake(take, timestamp) {
  const spec = direction[take.id];
  if (!spec) throw new Error(`Missing progression direction for ${take.id}`);
  rewritePaths(take);
  take.objective = spec.purpose;
  take.animation_prompt = spec.prompt;
  take.shot_contract.story_purpose = spec.purpose;
  take.shot_contract.dramatic_question = 'Como a acao ja iniciada produz uma consequencia irreversivel sem qualquer reset corporal?';
  take.shot_contract.story_change = spec.storyChange;
  take.shot_contract.distinct_story_events = 1;
  take.shot_contract.reaction = spec.reaction;
  take.shot_contract.cut_motivation = `The irreversible action settles directly into the exact approved opening frame of ${take.transition.connects_to}.`;
  take.shot_contract.duration_reason = 'The H3 route requires 124 source frames; direction restricts them to one monotonic event and editorial delivery retimes the approved result to two seconds.';
  take.shot_contract.motion_beats = {
    start: `Inherit pose, contact and momentum exactly from ${take.transition.connects_from}; no preparation beat.`,
    middle: spec.middle,
    end: `Exact approved entry state of ${take.transition.connects_to}; hold consequence without reset.`,
  };
  take.shot_contract.action = spec.action;
  take.shot_contract.camera.movement = spec.camera;
  take.shot_contract.transition_motion_contract.camera_evidence = {
    movement: spec.camera,
    physical_translation: true,
    perspective_change: 'Foreground, fighters and throne change overlap coherently while the camera follows one direction only.',
  };
  take.shot_contract.transition_motion_contract.real_depth = {
    foreground: 'Existing chain, ice edge or cloth crosses at a different speed without hiding a pose reset.',
    midground: spec.action,
    background: 'One emperor, one throne, crowd and braziers preserve fixed arena geography.',
    differential_motion: 'Foreground moves fastest, the committed fight action remains readable in midground, and the arena shifts slowest.',
    occlusion_or_scale_change: 'Coherent scale and overlap change occurs without full-frame blackout or concealed character replacement.',
  };
  take.shot_contract.transition_motion_contract.internal_action = {
    primary_event: spec.action,
    independent_elements: [
      'cloth, frost or sand follows the existing momentum vector instead of reversing it',
      'brazier flames and crowd react after the physical consequence',
    ],
    camera_independent: true,
  };
  take.shot_contract.transition_motion_contract.progression = {
    start: `inherited irreversible exit state of ${take.transition.connects_from}`,
    middle: spec.middle,
    end: `matched entry state of ${take.transition.connects_to} with no reset`,
    end_state_change: spec.storyChange,
    exit_or_cut: `direct exact-frame match into ${take.transition.connects_to}`,
  };
  take.shot_contract.temporal_progression_contract = {
    required: true,
    entry_momentum: `Inherit all body velocity, contact and limb extension from ${take.transition.connects_from}.`,
    irreversible_action: spec.action,
    reaction: spec.reaction,
    exit_state: spec.storyChange,
    monotonic_rules: [
      'distance, advantage or consequence advances in only one direction',
      'an extended attacking limb never retracts to repeat the same strike',
      'the attacker never returns to guard or idle inside the bridge',
      'camera movement never hides a pose replacement',
    ],
  };
  take.shot_contract.negative_rules = [
    'no rollback or motion vector reversal',
    'no pose reset, guard reset or return to idle',
    'no repeated wind-up, repeated strike or repeated contact',
    'no attacker backstep or forward-back-forward movement',
    'no flip, somersault, complete roll or gratuitous spin',
    'no full-frame occlusion hiding a pose jump',
    'no camera direction reversal or axis crossing',
    'no teleport, identity drift, mask removal, extra fighter or duplicated emperor',
    'no static tail',
  ];
  take.video = {
    status: 'pending_generation',
    output_preview: '',
    output_active: '',
    output_review_candidate: '',
    upscale_status: '',
    latent_file: '',
  };
  take.qc = {
    status: 'pending_generation',
    transition_motion_gate: {
      status: 'pending', evident_camera: false, real_depth: false, internal_action: false,
      clear_progression: false, evidence: 'pending V2 reviewed MP4 and contact sheet',
    },
    temporal_progression_gate: {
      status: 'pending', forward_momentum: false, no_reset: false,
      single_irreversible_event: false, exact_end_match: false,
      evidence: 'pending frame-by-frame human review',
    },
  };
  take.maestro_status = 'READY';
  take.maestro_last_job_id = '';
  take.maestro_last_error = '';
  take.maestro_last_result = null;
  take.maestro_upscale_status = '';
  take.maestro_upscale_error = '';
  take.maestro_updated_at = timestamp;
  delete take.maestro_notes;
  return take;
}

function updateProductionTake(take) {
  const spec = direction[take.id];
  if (!spec) throw new Error(`Missing progression direction for ${take.id}`);
  rewritePaths(take);
  take.transition_motion_contract = {
    camera_evidence: {
      movement: spec.camera,
      physical_translation: true,
      perspective_change: 'Foreground, fighters and throne change overlap coherently while camera translation keeps one direction.',
    },
    real_depth: {
      foreground: 'Existing chain, ice edge or cloth moves at a different speed without hiding a pose reset.',
      midground: spec.action,
      background: 'One emperor, one throne, crowd and braziers preserve fixed arena geography.',
      differential_motion: 'Foreground moves fastest, fight action remains readable in midground, arena shifts slowest.',
      occlusion_or_scale_change: 'Coherent overlap and scale change without full-frame blackout or concealed replacement.',
    },
    internal_action: {
      primary_event: spec.action,
      independent_elements: [
        'cloth, frost or sand follows the existing momentum vector',
        'brazier flames and crowd react after the consequence',
      ],
      camera_independent: true,
    },
    progression: {
      start: `inherited irreversible exit state of ${take.transition.connects_from}`,
      middle: spec.middle,
      end: `matched entry state of ${take.transition.connects_to} with no reset`,
      end_state_change: spec.storyChange,
      exit_or_cut: `direct exact-frame match into ${take.transition.connects_to}`,
    },
  };
  take.temporal_progression_contract = {
    required: true,
    entry_momentum: `Inherit pose, contact and body velocity from ${take.transition.connects_from}.`,
    irreversible_action: spec.action,
    reaction: spec.reaction,
    exit_state: spec.storyChange,
    forbidden: ['rollback', 'pose reset', 'guard reset', 'repeated wind-up', 'repeated strike', 'camera-hidden pose swap'],
  };
  take.qc = {
    status: 'pending_visual_generation',
    transition_motion_gate: {
      status: 'pending', evident_camera: false, real_depth: false, internal_action: false,
      clear_progression: false, evidence: 'pending V2 reviewed MP4 and contact sheet',
    },
    temporal_progression_gate: {
      status: 'pending', forward_momentum: false, no_reset: false,
      single_irreversible_event: false, exact_end_match: false,
      evidence: 'pending frame-by-frame human review',
    },
  };
  return take;
}

const timestamp = new Date().toISOString();
const queue = readJson(path.join(sourceRoot, 'take_queue.json'));
rewritePaths(queue);
queue.project_id = projectId;
queue.methodology = 'seven_minimax_h3_first_last_frame_bridges_strict_monotonic_progression_v2';
queue.status = 'READY_FOR_SERIAL_GENERATION';
queue.updated_at = timestamp;
queue.temporal_progression_gate = {
  required: true,
  rule: 'Every bridge inherits existing momentum and produces one irreversible consequence without reset, repeated wind-up, rollback or camera-hidden pose swap.',
  required_fields: ['forward_momentum', 'no_reset', 'single_irreversible_event', 'exact_end_match'],
};
queue.takes = queue.takes.map((take) => updateTake(take, timestamp));
fs.writeFileSync(path.join(targetRoot, 'take_queue.json'), `${JSON.stringify(queue, null, 2)}\n`, 'utf8');

const production = readJson(path.join(sourceRoot, 'production_manifest.json'));
rewritePaths(production);
production.project_id = projectId;
production.sequence_id = 'mortal_kombat_brothers_transition_progression_v2';
production.updated_at = timestamp;
production.temporal_progression_gate = queue.temporal_progression_gate;
production.takes = production.takes.map((take) => updateProductionTake(take));
fs.writeFileSync(path.join(targetRoot, 'production_manifest.json'), `${JSON.stringify(production, null, 2)}\n`, 'utf8');

const manifest = readJson(path.join(sourceRoot, 'project_manifest.json'));
manifest.project_id = projectId;
manifest.title = 'Mortal Kombat - Conectores H3 - Progressao V2 sem rollback';
manifest.objective = 'Refazer os sete conectores com uma unica acao irreversivel por ponte, continuidade de impulso e proibicao de reset corporal.';
manifest.created_at = timestamp;
manifest.updated_at = timestamp;
manifest.status = 'IN_PROGRESS';
manifest.maestro_status = 'READY_FOR_SERIAL_GENERATION';
manifest.render_authorized = true;
manifest.render_authority = 'owner explicitly rejected all V1 bridges and ordered complete monotonic-progression regeneration on 2026-08-14';
manifest.video_generation.delivery_contract = 'Generate all seven 124-frame H3 bridges serially; approve only monotonic action, then retime each to exactly 2 seconds. Preserve prior master as rollback until V2 owner review.';
manifest.video_generation.progression_contract = 'inherit momentum -> one irreversible action -> visible consequence -> exact next-take frame; no reset or reversal';
fs.writeFileSync(path.join(targetRoot, 'project_manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');

console.log(JSON.stringify({ ok: true, projectId, targetRoot, takes: queue.takes.length }, null, 2));
