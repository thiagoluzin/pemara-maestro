# Seleção por decisão e fase

Fonte operacional única para encaminhamento Pemara, 2026-10-08. As skills citadas estão em `E:/Pemara/.agents/skills/<nome>/SKILL.md`, salvo caminho explícito. Ler apenas a linha pertinente e os especialistas que alteram a decisão atual. Até três primárias por fase; gates adicionais quando necessários.

| Pedido / entrada | Responsável e saída | Limite / encaminhamento |
|---|---|---|
| Ideia ou revisão de filme | `pemara-video-production-lead`: sequência e fichas | Combate → `pemara-live-action-combat-director`; atuação → `pemara-performance-director`; fotografia → `pemara-cinematography-director` |
| Montagem narrativa | `pemara-film-editor`: seleção, ritmo e cortes | Codec/mux/execução → `video-production`; compatibilidade física → `pemara-live-action-kinetic-supervisor` |
| Inspecionar um vídeo existente ou explicar marcadores | [pemara-video-inspection](C:/Users/admin_remoto/.codex/skills/pemara-video-inspection/SKILL.md) para triagem e explicação das evidências | Explicações de marcadores existentes usam os arquivos locais do job. Uma análise nova segue a autorização de envio da mídia e o orçamento definidos na skill. A inspeção termina na revisão. |
| Qualidade artística de um take live action em produção | `pemara-live-action-qc`: observação temporal por dimensão | Continuidade → `pemara-live-action-continuity`; técnico não aprova arte |
| Controles H3 / takes | `pemara-live-action-showrunner`, `pemara-cinematic-take-director` ou `pemara-video-motion-director` pelo risco | Não trocar motor nem obter pose exata por promessa textual; ComfyUI do Codex via MCP |
| Intro de jogo por takes | `ai-video-intro-pipeline`: pipeline de intro no projeto | Reutiliza direção de vídeo; respeita contrato específico de FFVIII quando aplicável |
| Imagem / keyframe | `image-production`: imagem fiel e QC | Ferramenta conforme stack/autorização; acabamento visual vigente; não escolher nova stack por nome |
| Música completa / correção artística | `pemara-music-production-lead`: intenção e plano | Composição/letra → `pemara-music-songwriter`; arranjo → `pemara-music-arranger`; mix → `pemara-music-mix-engineer`; escuta → `pemara-music-listening-qc`. Fluxo obrigatório por fase; papéis não exigem subagentes. |
| Heavy metal / thrash metal / punk rock / death metal | `pemara-heavy-metal`, `pemara-thrash-metal`, `pemara-punk-rock` ou `pemara-death-metal`, conforme o gênero | Sob o produtor musical; decisões de riff, groove, voz e forma específicas. Configurações em `C:/Users/admin_remoto/.codex/agents/`; perfis apontam para skills canônicas. Instalação não inicia agentes nem geração. |
| Canto de uma música | `pemara-music-vocal-director`: prosódia e interpretação | Complementa o gênero; revisão de emissão no áudio, sem clonagem ou aprovação por ASR. Fala/TTS continua na direção de voz falada. |
| Lote/álbum e músicas repetitivas | `pemara-music-album-diversity`: comparação de hooks, motivos, groove e fraseado | Comparar plano e áudios reais; identidade de banda pode permanecer. Não regenerar lote cancelado nem confundir novos seeds com composição nova. |
| Voz / interpretação falada | `pemara-voice-performance-director`: performance e QC vocal | Áudio exato/consentimento e provedor autorizado; música não é clonagem de voz |
| Análise ou integração de áudio | `audio-analysis` ou `game-audio-reactive`: medição ou integração | Criação de SFX/música de jogo → `game-audio-designer` |
| Escopo/arquitetura/dependências | `project-planner`: plano proporcional e verificável | `spec-driven-development` e `planning-and-task-breakdown` são entradas por modo do mesmo planejamento; execução → `incremental-implementation` |
| Erro reproduzível ou incidente | `debugger`: causa, correção e evidência | `debugging-and-error-recovery` encaminha a mesma família; sistema desconhecido → `code-archaeologist` |
| Lentidão / memória / profiling | `performance-optimizer`: baseline e melhoria medida | `performance-optimization` encaminha por módulo; GPU e Unity usam ferramentas da stack escolhida |
| Métricas após execução ComfyUI conduzida pelo agente | [performance-optimizer](../../performance-optimizer/SKILL.md) e [procedimento pós-ComfyUI](../../performance-optimizer/references/post-comfyui.md) | Usar o canal autorizado para medir tempo, RAM e VRAM; a interpretação semântica segue a regra Decision do projeto. |
| Testar uma função, componente ou contrato de API | [test-engineer](../../test-engineer/SKILL.md) para regressões unitárias e de integração | Usar o menor teste que observe a falha. |
| Regressão de fluxo no navegador, suíte E2E ou infraestrutura de testes na CI | [qa-automation-engineer](../../qa-automation-engineer/SKILL.md) para cenários de ponta a ponta e execução na CI | Reutilizar a suíte e os dados isolados do projeto. |
| HTML/CSS/JS sem framework | `web-frontend-vanilla`: interface acessível | `vanilla-web-patterns` fornece exemplos; outra stack → `frontend-ui-engineering`, preservando stack existente |
| Segurança online | `pemara-online-security-guardian`: fronteira e evidência de liberação | `saas-pentest-hardening`/`security-and-hardening`: técnicas; não autorizam scans ativos fora do escopo |
| Jogo do conceito ao jogável | `game-build-flow` / `game-developer`: execução no motor escolhido | `creative-director` conceitua; `demo-release-engineer` empacota apenas stack aplicável |
| Phaser plataforma | `phaser-platformer-architect`: arquitetura/feel | `phaser-16bit-platformer`: receitas; `phaser-animation-turbo`: runtime de animação |
| Examinar quadros, atlas ou escala aparente de um sprite | [sprite-image-reading](../../sprite-image-reading/SKILL.md) mede os quadros existentes | Para corrigir escala dos heróis de Ritmos da Revolta, seguir [hero-sprite-scaling](../../hero-sprite-scaling/SKILL.md). |
| Implementar timing, estados ou eventos da animação de um sprite no jogo | [sprite-animation](../../sprite-animation/SKILL.md) | Confirmar o motor do projeto e as poses já aprovadas. |
| Pintar, animar ou revisar no Krita quando essa ferramenta foi escolhida | [Pintura](C:/Users/admin_remoto/.codex/skills/krita-mcp-workflow/SKILL.md), [ciclo de sprites](C:/Users/admin_remoto/.codex/skills/krita-sprite-animation/SKILL.md) ou [crítica independente](C:/Users/admin_remoto/.codex/skills/krita-art-review/SKILL.md), conforme o pedido | Respeitar a ferramenta autorizada para o projeto. |
| Beat-em-up / balanceamento | `beatemup-combat-designer` ou `balance-tuner`: mecânica jogável | Diferente da direção de luta filmada; respeitar gênero/motor |
| Unity | Skill Unity pertinente em `C:/Users/admin_remoto/.agents/skills` ou plugin disponível | Não migrar para Phaser por causa do catálogo Pemara |
| Godot / outro motor existente | Código e documentação da versão do projeto, especialista disponível compatível | Não inventar skill nem trocar stack; `game-developer` pode coordenar |
| HyperFrames | `C:/Users/admin_remoto/.agents/skills/hyperframes/SKILL.md`: composição nessa stack | `general-video` é HyperFrames; não é rota de geração H3 no Maestro |
| Sprunki LoRA | `sprunki-lora-trainer`: treino/avaliação no escopo | Pausas, dataset, GPU e aprovação próprios |
| Automação | `automation-engineer`: rotina verificável | Não criar monitor sem solicitação; fronteira online exige guardian |
| Catálogo / aliases / auditoria de skills | `pemara-ecosystem-orchestrator`: inventário e manutenção | O encaminhamento operacional continua neste mapa |
| NVIDIA/TAO/NeMo/Jetson | Skill específica quando a stack/pedido exigir | Não carregar o pacote inteiro ou instalar por descoberta |

Saída de uma fase vira entrada explícita da próxima: artefato, versão, caminho/hash quando relevante, decisão, pendências e autorização já estabelecida. Não reiniciar briefing a cada encaminhamento.
