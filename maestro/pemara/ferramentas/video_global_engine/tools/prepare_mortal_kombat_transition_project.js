const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const root = 'E:\\Pemara\\maestro\\pemara\\ferramentas\\video_global_engine\\projetos\\mortal_kombat_irmaos_transicoes_h3';
const keyframes = path.join(root, 'keyframes');
const now = new Date().toISOString();

const specs = [
  {
    id: 'B01_02', from: '01', to: '02', slug: 'corrida_ao_primeiro_choque',
    purpose: 'Transformar o plano geral distante no primeiro contato corpo a corpo sem salto de escala.',
    question: 'Qual irmao alcanca o centro e bloqueia primeiro?',
    change: 'Os rivais distantes atravessam a areia e terminam travados em um choque de antebracos.',
    camera: 'fast low physical dolly through the arena, passing behind a heavy foreground chain and rising into a medium two-shot',
    perspective: 'the foreground chain sweeps across the lens while the fighters grow coherently and the throne separates behind them',
    foreground: 'a heavy hanging chain and a near brazier cross close to the lens',
    midground: 'both masked brothers sprint from opposite sides and collide at center',
    background: 'the emperor, throne and crowd remain fixed in geography while parallax changes their overlap',
    event: 'both fighters accelerate, kick up two distinct sand trails and meet in one armored forearm parry',
    elements: ['two separate sand trails follow the fighters independently', 'brazier flames and crowd bodies react independently'],
    prompt: 'Create one continuous ultra-photorealistic live-action transition between the exact supplied first and last frames. Preserve the exact blue masked cryomancer, black hooded shadow revenant, emperor, arena, screen axis, costumes and body proportions. The camera performs a fast low physical dolly through the arena, briefly passing behind the existing heavy foreground chain, while both brothers sprint from opposite sides. Their separate boots throw realistic sand trails; armor, cloth, braziers and crowd react independently. End naturally in the exact supplied medium two-shot as their armored forearms collide. Realistic mass, acceleration and foot traction; no teleport, no cut and no pose reset.',
  },
  {
    id: 'B02_03', from: '02', to: '03', slug: 'bloqueio_para_gelo_e_sombra',
    purpose: 'Converter o clinche fisico no primeiro uso legivel de gelo e sombra.',
    question: 'Quem quebra o contato e revela primeiro seu poder?',
    change: 'O clinche equilibrado se rompe; gelo nasce no braco azul enquanto a sombra negra recua.',
    camera: 'short physical orbit around the locked forearms, ending over the blue fighter shoulder',
    perspective: 'the emperor shifts behind the fighters as the camera arcs and the foreground shoulder changes occlusion',
    foreground: 'blue armored shoulder, frost crystals and one passing cloth edge',
    midground: 'locked forearms separate as ice forms and shadow cloth recoils',
    background: 'throne, crowd and braziers slide at a slower differential rate',
    event: 'the blue fighter twists free, frost races over his gauntlet and the black fighter recoils into dry shadow',
    elements: ['frost grows directionally across the gauntlet', 'shadow cloth and brazier flames react separately'],
    prompt: 'Create one continuous ultra-photorealistic live-action transition between the exact supplied first and last frames. Preserve both exact masked brothers, costumes, arena axis and emperor. Execute a short physical orbit around their locked forearms. The blue cryomancer twists free and frost grows directionally over his gauntlet; the black hooded revenant recoils with dry shadow cloth trailing, while braziers and crowd react independently. End exactly in the supplied powered combat stance. Real body torque, armor inertia and sand traction; no cut, no teleport, no extra fighter and no identity drift.',
  },
  {
    id: 'B03_04', from: '03', to: '04', slug: 'onda_de_gelo_para_clinche',
    purpose: 'Levar o ataque de gelo no solo ate o novo contato fisico sem mudar arbitrariamente a geografia.',
    question: 'A sombra escapara da onda de gelo antes do clinche?',
    change: 'A onda de gelo e evitada e a distancia fecha ate um novo bloqueio de joelho e bracos.',
    camera: 'ground-level lateral tracking move following the ice ridge before lifting into the clinch',
    perspective: 'ice spikes race fastest across foreground while fighters close in midground and the throne drifts slowly',
    foreground: 'moving ice ridge, crystals and sand displaced close to the lens',
    midground: 'black revenant sidesteps the ice and closes on the blue fighter',
    background: 'crowd, banners, throne and braziers preserve their established axis',
    event: 'the ice ridge crosses, the black fighter steps around it and both meet in a controlled grapple',
    elements: ['ice crystals break and scatter independently', 'banners and fire react independently to the rush'],
    prompt: 'Create one continuous ultra-photorealistic live-action transition between the exact supplied first and last frames. Preserve both exact masked brothers, costumes, arena, throne and screen direction. Track physically at ground level beside the moving ice ridge; sharp crystals and sand cross the foreground. The black hooded revenant sidesteps with believable weight, closes the distance and meets the blue cryomancer in the exact supplied controlled grapple. The camera lifts as they connect; banners, fire and crowd move independently. No cut, no sliding feet, no morphing, no duplicate limbs and no identity drift.',
  },
  {
    id: 'B04_05', from: '04', to: '05', slug: 'equilibrio_para_vantagem_da_sombra',
    purpose: 'Dar origem fisica e legivel a vantagem temporaria do irmao de sombra.',
    question: 'Como Bi-Han rompe o equilibrio do corpo a corpo?',
    change: 'A troca equilibrada termina com a sombra atravessando a guarda e deslocando Kuai.',
    camera: 'tight physical truck and quarter-orbit following the black fighter through a foreground shadow occlusion',
    perspective: 'the shadow cape briefly occludes the lens while the fighters exchange sides and the throne changes overlap',
    foreground: 'black cape and armor pass close across the lens',
    midground: 'the black fighter slips outside the guard and drives a heavy elbow',
    background: 'throne, braziers and crowd remain coherent through the side exchange',
    event: 'a shadow-assisted sidestep opens the guard and produces one heavy armored elbow consequence',
    elements: ['cape and dry shadow trail move independently', 'ice dust and crowd recoil move independently'],
    prompt: 'Create one continuous ultra-photorealistic live-action transition between the exact supplied first and last frames. Preserve the exact blue masked cryomancer and black hooded revenant, their masks, armor and arena axis. Use a tight physical truck with a quarter-orbit as the black cape crosses the foreground and briefly occludes the lens. The black fighter performs one grounded outside sidestep and a heavy armored elbow that breaks the blue fighter guard. Ice dust, cape, braziers and crowd react independently. End exactly in the supplied shadow-advantage position. No teleport, no weightless spin, no cut and no identity drift.',
  },
  {
    id: 'B05_06', from: '05', to: '06', slug: 'queda_para_contragolpe_congelante',
    purpose: 'Transformar a queda de Kuai na recuperacao que inicia o golpe congelante decisivo.',
    question: 'Kuai conseguira levantar antes do ataque seguinte?',
    change: 'Kuai sai do solo, recupera a base e intercepta o avanco de Bi-Han com a palma fria.',
    camera: 'low physical push beside the fallen fighter, rising with him into the counterattack',
    perspective: 'foreground ice and sand slide past quickly while bodies rise and the throne remains deep behind them',
    foreground: 'broken ice, sand spray and one boot pass close to the lens',
    midground: 'blue fighter rolls to one knee, rises and catches the incoming black arm',
    background: 'emperor, crowd and fires remain geographically locked with slower parallax',
    event: 'the blue fighter plants a boot, rises under pressure and intercepts the incoming strike with cold energy',
    elements: ['broken ice skids independently across sand', 'black cloth and brazier flames react independently'],
    prompt: 'Create one continuous ultra-photorealistic live-action transition between the exact supplied first and last frames. Preserve both exact masked brothers, costumes, arena and throne. Begin low beside the fallen blue fighter with broken ice in the foreground. The camera physically pushes and rises as he rolls to one knee, plants his boot and intercepts the black revenant incoming arm with a cold palm. Ice pieces skid, sand sprays, cloth and braziers react independently. End exactly in the supplied decisive counter position. Realistic recovery timing and body mass; no teleport, no rubber limbs, no cut and no identity drift.',
  },
  {
    id: 'B06_07', from: '06', to: '07', slug: 'atordoamento_para_ordem_imperial',
    purpose: 'Criar uma respiracao dramatica entre o congelamento decisivo e a ordem do imperador.',
    question: 'O imperador interrompera o silencio apos Bi-Han cair de joelhos?',
    change: 'Bi-Han permanece atordoado; Kuai recua meio passo e a autoridade do trono domina a composicao.',
    camera: 'physical crane rise from the frozen kneeling fighter toward the throne, then settle back into the supplied arena axis',
    perspective: 'foreground frost and chain descend across frame while fighters and throne separate strongly in depth',
    foreground: 'frost vapor, cracked ice and a heavy chain cross close to the lens',
    midground: 'black fighter remains stunned while blue fighter releases pressure and turns toward the throne',
    background: 'the emperor rises into dominance as crowd and fire recoil',
    event: 'the frozen fighter drops weight to one knee and the blue fighter turns as the emperor stands',
    elements: ['frost vapor and ice cracks evolve independently', 'emperor cape, crowd and braziers react independently'],
    prompt: 'Create one continuous ultra-photorealistic live-action transition between the exact supplied first and last frames. Preserve the exact blue masked cryomancer, black hooded revenant, emperor, throne and arena. Physically crane upward from cracked foreground ice and the stunned kneeling black fighter toward the emperor as he rises with heavy cape movement; the blue fighter releases pressure and turns toward the throne. A chain changes foreground occlusion, while crowd, frost vapor and braziers react independently. Settle naturally into the exact supplied arena axis. No dialogue, no cut, no new person, no mask change and no identity drift.',
  },
  {
    id: 'B07_08', from: '07', to: '08', slug: 'decisao_para_agarrada_final',
    purpose: 'Ligar a decisao silenciosa de Kuai ao primeiro contato do golpe final.',
    question: 'Kuai obedecera e executara o golpe?',
    change: 'Kuai fecha a distancia e termina com as duas maos firmes no oponente atordoado.',
    camera: 'restrained physical arc behind the blue fighter shoulder into the final frontal grip',
    perspective: 'blue shoulder and a foreground chain change overlap while the black fighter grows and throne recedes',
    foreground: 'blue shoulder, forearm frost and one chain edge pass close to the lens',
    midground: 'blue fighter advances one grounded step and establishes the final two-hand grip',
    background: 'emperor, throne, crowd and braziers remain fixed and readable',
    event: 'the blue fighter closes his fist, advances and takes a firm two-hand grip on the stunned opponent',
    elements: ['forearm frost tightens and sheds crystals independently', 'black shadow cloth and crowd recoil move independently'],
    prompt: 'Create one continuous ultra-photorealistic live-action transition between the exact supplied first and last frames. Preserve the exact blue masked cryomancer, black hooded revenant, emperor, arena, masks, armor and body proportions. Perform a restrained physical arc behind the blue fighter shoulder. He closes his frosted fist, takes one grounded step and establishes the exact supplied two-hand grip on the stunned opponent. Foreground chain, frost crystals, black cloth, braziers and crowd move independently. End firmly in the supplied grip with no strike yet. No cut, no teleport, no face exposure, no extra fingers and no identity drift.',
  },
];

const sha = (file) => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');

const makeContract = (spec) => ({
  story_purpose: spec.purpose,
  dramatic_question: spec.question,
  story_change: spec.change,
  distinct_story_events: 2,
  reaction: 'Both brothers and the arena environment react visibly to the connecting physical event.',
  cut_motivation: `The exact last frame resolves into the approved opening state of Take ${spec.to}.`,
  duration_reason: 'The H3 source uses its minimum trained 124-frame window; editorial delivery retimes the complete bridge to two seconds.',
  motion_beats: {
    start: `Exact approved boundary frame from Take ${spec.from}.`,
    middle: spec.event,
    end: `Exact approved boundary frame from Take ${spec.to}.`,
  },
  transition_motion_contract: {
    camera_evidence: { movement: spec.camera, physical_translation: true, perspective_change: spec.perspective },
    real_depth: {
      foreground: spec.foreground,
      midground: spec.midground,
      background: spec.background,
      differential_motion: 'foreground occluders travel fastest, fighters move at a readable middle rate and throne/crowd shift slowest',
      occlusion_or_scale_change: spec.perspective,
    },
    internal_action: { primary_event: spec.event, independent_elements: spec.elements, camera_independent: true },
    progression: {
      start: `approved exit state of Take ${spec.from}`,
      middle: spec.event,
      end: `approved entry state of Take ${spec.to}`,
      end_state_change: spec.change,
      exit_or_cut: `exact last-frame match into Take ${spec.to}`,
    },
  },
});

const takes = specs.map((spec, index) => {
  const start = path.join(keyframes, `bridge_${spec.from}_${spec.to}_start.png`);
  const end = path.join(keyframes, `bridge_${spec.from}_${spec.to}_end.png`);
  if (!fs.existsSync(start) || !fs.existsSync(end)) throw new Error(`Missing bridge keyframes for ${spec.id}`);
  return {
    id: spec.id,
    slug: spec.slug,
    sequence: index + 1,
    role: 'continuity_bridge_minitake',
    is_transition: true,
    transition: { is_transition: true, connects_from: `Take ${spec.from}`, connects_to: `Take ${spec.to}` },
    objective: spec.purpose,
    target_duration_seconds: 5.125,
    editorial_use_seconds: 2.0,
    animation_prompt: spec.prompt,
    base_image: {
      status: 'approved_for_video', file: start, image_sha256: sha(start),
      source: `approved FHD Take ${spec.from} boundary frame`, approved_at: now,
    },
    shot_contract: {
      ...makeContract(spec),
      subject: 'The exact approved blue masked cryomancer and black hooded shadow revenant brothers.',
      action: spec.event,
      scene: 'The exact approved basalt imperial arena with emperor, throne, crowd, chains, braziers, ice and sand continuity.',
      camera: { movement: spec.camera, angle: 'continuity-driven dynamic eye-to-low angle', lens: 'cinematic 28-40 mm equivalent', focus: 'fighters locked with readable three-plane depth' },
      lighting: 'cold moonlight and independent amber brazier motion preserved from both anchors',
      mood: 'tragic, brutal and continuous',
      visual_references: {
        start_frame: start, start_frame_json: '', end_frame: end, end_frame_json: '',
        end_frame_file: end, end_frame_approved: true, end_frame_sha256: sha(end),
        style_refs: [], object_refs: [],
      },
      variants: { count: 1, duration_seconds: 5.125, select_before_final: true },
      negative_rules: ['no internal cut', 'no teleport', 'no identity drift', 'no mask removal', 'no extra fighter', 'no pose reset', 'no static tail'],
    },
    video_generation: {
      profile: 'minimax_h3_fl2va_int8_ltx_contract_720p24', width: 1280, height: 720,
      fps: 24, frames: 124, steps: 20, guidance: 1.0,
      camera_pose: '', camera_speed: 0.8, start_end_frame_enabled: true,
    },
    audio_direction: {
      strategy: 'hunyuan_video_foley_after_visual_approval', delivery_required: false,
      post_mix_required: true, dialogue_generation_authorized: false, human_listening_required: true,
    },
    video: { status: 'planned', output_preview: '', output_active: '', upscale_status: 'not_started' },
    qc: {
      status: 'pending_visual_generation',
      transition_motion_gate: { status: 'pending', evident_camera: false, real_depth: false, internal_action: false, clear_progression: false, evidence: 'pending reviewed MP4 and contact sheet' },
    },
    maestro_status: 'PENDING',
  };
});

const queue = {
  schema_version: '1.4', project_id: path.basename(root),
  methodology: 'seven_minimax_h3_first_last_frame_bridges_human_qc_then_2s_editorial_retime',
  status: 'TRANSITION_CONTRACTS_READY_PILOT_PENDING', updated_at: now,
  engine_policy: {
    authority: 'owner_directive', status: 'ACTIVE_FOR_THIS_PROJECT_ONLY', engine: 'MiniMax H3 FL2VA',
    profile: 'minimax_h3_fl2va_int8_ltx_contract_720p24', native_audio_authorized: false,
    frames_per_take: 124, take_count: 7, serial_generation_required: true, silent_model_substitution_forbidden: true,
  },
  universal_transition_motion_gate: {
    required: true, policy_version: '1.0',
    pillars: ['evident_camera', 'real_depth', 'internal_action', 'clear_progression'],
  },
  global_negative_rules: ['scene cut inside a bridge', 'teleport', 'identity drift', 'mask removal', 'extra fighter', 'text', 'logo', 'static tail'],
  takes,
};

const production = {
  schema_version: '1.0', project_id: path.basename(root), sequence_id: 'mortal_kombat_transition_bridges',
  role: 'transition_minitakes', updated_at: now,
  universal_transition_motion_gate: queue.universal_transition_motion_gate,
  takes: takes.map((take) => ({
    id: take.id, slug: take.slug, role: take.role, is_transition: true,
    transition: take.transition, transition_motion_contract: take.shot_contract.transition_motion_contract,
    qc: take.qc,
  })),
};

const manifest = {
  schema_version: '1.2', project_id: path.basename(root),
  title: 'Mortal Kombat - Conectores de Transicao H3',
  objective: 'Gerar sete minitakes first/last-frame para corrigir todos os cortes secos do filme aprovado.',
  duration_target_seconds: 14.0, source_duration_seconds: 35.875,
  preview_resolution: '1280x720', final_resolution: '1920x1080', fps_preview: 24, fps_final: 60,
  created_at: now, updated_at: now, status: 'IN_PROGRESS', maestro_status: 'IN_PROGRESS',
  render_authorized: true, render_authority: 'owner explicitly requested transition repair on 2026-08-14',
  take_queue: 'take_queue.json',
  audio: { music_provider: 'none', foley_provider: 'HunyuanVideo-Foley XXL after visual approval', voice_provider: 'none in bridges', native_h3_audio: 'disabled' },
  video_generation: {
    preferred_profile: 'minimax_h3_fl2va_int8_ltx_contract_720p24', engine: 'MiniMax H3 FL2VA INT8 + Qwen3-VL-32B',
    native_contract: '1280x720, 24 fps, 124 frames with exact approved first and last frames',
    delivery_contract: 'retime each approved 5.125-second source bridge to 2.0 seconds, upscale and interpolate only after human QC',
    take_count: 7, silent_model_substitution_forbidden: true, local_gpu: 'RTX 5090',
  },
};

fs.mkdirSync(root, { recursive: true });
fs.writeFileSync(path.join(root, 'take_queue.json'), `${JSON.stringify(queue, null, 2)}\n`);
fs.writeFileSync(path.join(root, 'production_manifest.json'), `${JSON.stringify(production, null, 2)}\n`);
fs.writeFileSync(path.join(root, 'project_manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);
console.log(JSON.stringify({ ok: true, root, takeCount: takes.length }, null, 2));
