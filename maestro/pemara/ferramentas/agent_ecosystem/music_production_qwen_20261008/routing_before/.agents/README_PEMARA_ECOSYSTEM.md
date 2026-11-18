# Pemara Agent Ecosystem

Camada operacional de agentes e skills da Pemara.

## Auditoria atual

Relatorio principal:

`E:/Pemara/maestro/pemara/ferramentas/agent_ecosystem/AUDITORIA_novo_analisar_20260704.md`

Fonte importada:

`E:/Pemara/novo_analisar`

## Skills Pemara mais importantes

- `pemara-messenger-turbo`: roteador canônico; elimina cópias entre skills e perfis, limita o conjunto ativo e aplica gates transversais.
- `agents-turbo`: perfil dispatcher mestre para tarefas multidomínio; coordena sem duplicar instruções especializadas.
- `pemara-online-security-guardian`: agente/gate transversal para RLS, autorização backend, IDOR, segredos, inputs/XSS e release online com evidências.
- `pemara-video-motion-director`: direcao e QC de movimento para video generativo.
- `ai-video-intro-pipeline`: pipeline completo de intro/cutscene por takes.
- `image-production`: geracao/edicao/QC de imagens e keyframes.
- `video-production`: montagem, ffmpeg, codec, contact sheet e saida final.
- `creative-director`: roteiro, conceito, prompt e especificacao executavel.
- `sprunki-lora-trainer`: treino, dataset, QC e promocao de LoRA Sprunki.
- `game-audio-designer`: musica, SFX, audio reativo e analise de som.
- `pemara-voice-performance-director`: roteiro falado, locucao, sotaque, interpretacao e selecao de voz; perfil alias no Agents Turbo.
- `phaser-animation-turbo`: sprites Phaser, escala runtime, frames, animacoes e gates.
- `sprite-image-reading`: leitura/fatiamento/auditoria de spritesheets.
- `animation-engineer`: principios de animacao 2D e humanizacao de movimentos.
- `qa-automation-engineer`: Playwright/E2E/regressao.
- `performance-optimizer`: performance, bundle, memoria, CPU/GPU e profiling.

## Regra de video — revisão 2026-10-08

Começar por [pemara-video-production-lead](skills/pemara-video-production-lead/SKILL.md). Planejar a experiência do público, a sequência e cada take antes do prompt. Atuação, fotografia, identidade, ação e montagem precisam de decisões próprias e revisão do arquivo real.

| Agente/skill | Responsabilidade |
|---|---|
| `pemara-video-production-lead` | produção completa, roteiro visual, riscos e correções |
| `pemara-cinematography-director` | composição, blocking, câmera motivada, luz e geografia |
| `pemara-performance-director` | intenção, escuta, gesto, peso, reação e recuperação |
| `pemara-film-editor` | seleção, ritmo, cobertura, cortes e revisão da sequência |

São papéis sequenciais, sem obrigação de criar subagentes. O roteador mantém no máximo três skills primárias por fase. Os especialistas existentes de combate, continuidade, movimento, voz e QC continuam responsáveis pelos seus gates.

Fluxo: intenção → sequência/identidade → direção de atuação e fotografia → âncoras aprovadas → contrato executável → geração autorizada → revisão integral dos takes → aprovação exata das fontes → montagem/revisão do filme → picture lock aprovado → acabamento obrigatório → nova avaliação.

Maestro: MiniMax H3 com Sage + Spectrum, sem LTX/fallback. Acabamento: SeedVR2 3B int8 → RIFE 4.25 exato 60 FPS → DLSS 5 Natural com cópia do áudio existente. Não reabrir projetos históricos nem gerar por uma atualização de skills. Completar plano ou testes não aprova qualidade artística.

Revisão comum: [contrato de qualidade](skills/pemara-video-production-lead/references/production-quality-contract.md). Histórico da atualização: `E:/Pemara/maestro/pemara/ferramentas/agent_ecosystem/video_production_quality_20261008/LEIA_ME.md`.

## Regra de GPU

Quando a GPU estiver em descanso, trabalhar somente com:

- docs;
- prompts;
- JSON;
- pesquisa;
- auditoria;
- QC offline;
- organizacao de arquivos;
- preparacao de filas.

Nao iniciar treino, ComfyUI job, video, imagem ou inferencia local pesada durante descanso de GPU.

## Gate de Roteamento

Tarefa multidomínio deve passar por `pemara-messenger-turbo` / `agents-turbo`. Tarefa simples pode ir diretamente à skill específica:

1. identificar dominio: loja, Maestro, video, imagem, sprites/game, audio, automacao, infra, limpeza ou QA;
2. escolher no maximo 3 skills primarias;
3. ler as skills escolhidas antes de agir;
4. checar risco: producao, credenciais, GPU, locks e operacoes destrutivas;
5. usar caminhos canonicos existentes;
6. so carregar skills NVIDIA/TAO/NeMo/VSS quando a tarefa pedir essa stack explicitamente.

Perfis com marcador `AGENTS_TURBO_ALIAS_V1` são aliases de compatibilidade: a fonte de verdade é a skill homônima. Perfis especializados permanecem independentes e são enumerados no registro do Messenger Turbo.

## Gate de segurança online

Mudança em rota pública, autenticação, admin, upload, pagamento, tenant, banco,
gateway, túnel, webhook ou ferramenta de agente deve incluir
`pemara-online-security-guardian`. O gate exige teste negativo, segredo redigido,
validação do artefato implantado, rollback e decisão explícita. Build verde e
scanner sem alerta alto não equivalem sozinhos a liberação de segurança.

Excecao de GPU so vale quando o pedido atual do usuario autorizar GPU agora.
