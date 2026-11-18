# Atualização de direção, câmera e DLSS seletivo — 2026-10-09

Autorização: pedido do proprietário “pode atualizar tudo”, após revisão da V15 e proposta de melhoria. Alterações aplicadas às instruções canônicas e ao código; nenhuma geração de cena, download de modelo, envio TypeSafe, áudio novo ou alteração da entrega V15.

## O que mudou

- Nove skills: produção, fotografia, montagem, continuidade, supervisão cinética, QC, direção de takes, movimento e produção de imagens. AGENTS e referências comuns atualizados. Perfis de agentes continuam aliases dessas fontes, sem duplicação de regras.
- Novas sequências live action usam mapa compartilhado, estados/câmeras ligados ao espaço e bloco piloto que inclui uma fronteira. Revisão temporal desse bloco precede o lote. Registro de duas falhas equivalentes bloqueia repetição sem mudança documentada de método.
- Câmera fixa dirigida pode sustentar contato e reação; a exigência genérica de translação não força movimento em todo plano. Contratos específicos aprovados continuam válidos.
- `sequence_camera_contract.py` valida evidências, referências, fronteiras, piloto, corpos planejados, revisão e reparos. Geração e montagem Maestro consomem `sequence_camera_contract.json` quando presente na raiz do projeto; o catálogo/readiness também exibe esse gate. Não impõe migração aos projetos históricos. O validador não interpreta pixels, não confirma que uma pessoa assistiu e não concede aprovação artística.
- `actor_protection.py` compõe personagens da fonte anterior ao DLSS sobre o cenário NR. Máscaras explícitas vinculadas por hash e revisão são obrigatórias quando o modo é solicitado. Faltas e incompatibilidades bloqueiam sem tratamento integral silencioso.
- Imagens seletivas usam PNG/WebP sem perdas; vídeos exigem máscara por quadro, sem broadcast de foto. Composição em sRGB linear com alpha original. Interior branco das imagens conferido pixel a pixel; em vídeo com perdas, preservação é anterior à codificação.
- `dlss5_finishing.py` mantém modo integral e recibos históricos, acrescenta perfil seletivo e modalidades de processamento nas montagens mistas. Preserva original, intermediário NR, máscaras e proveniência; evita segunda passagem sobre fonte já tratada.
- Nó `PemaraSaveActorProtectedImage` instalado na extensão canônica e na cópia do runtime. Builder/template usam `ImageToMask(red)` para converter a máscara cinza, evitando confusão com alpha invertido de `LoadImage`.

## Validação

- **136 testes passaram**: composição de atores, contrato de câmera, acabamento integral existente, upscale, workflow H3 e projetos de vídeo.
- Incluído teste com FFmpeg CPU real: três quadros sintéticos compostos com máscara, interiores preservados, cenários substituídos e áudio PCM preservado. Não executou NR/GPU.
- As nove skills passaram no `quick_validate.py`; sintaxe dos módulos alterados compilada.
- **20 backups verificados por SHA-256**, com manifesto e hashes das versões alteradas. Nenhum backup foi sobrescrito. Novos módulos/templates são aditivos.
- Runtime ComfyUI verificado via MCP; fila real vazia antes de recarga. A primeira recarga ocorreu antes da cópia atualizada; a cópia foi então instalada e a recarga final confirmou o novo nó via `nodes(action="get")`, sem executar workflow.
- Fonte e cópia da extensão no runtime conferidas byte a byte. Runtime final: `D:/PemaraRuntimes/ComfyUI-v0.36.0-pemara`, porta 8188, PID 84788 no momento da verificação.
- V15 preservada: SHA-256 `d8f2b5ddc5ec48f15f92aa6c6d82700f87f7a1fe3ed8e6c4cd777f4c3bbb3a23` confirmado após as alterações.

## Limites observados

A composição seletiva está implementada e o nó foi carregado. **Não foi feito comparativo DLSS seletivo em atores reais nem qualificação artística do rastreamento de máscaras em vídeo.** Não há segmentação automática habilitada: as máscaras precisam ser produzidas e revisadas. Testes sintéticos verificam o código, não a naturalidade dos atores.

A proteção usa a fonte imediatamente anterior ao DLSS. Não desfaz alterações que já vieram da geração, de uma âncora artificial ou do SeedVR2; comparar as etapas continua obrigatório.

O backend Maestro foi atualizado em disco. Na inspeção local não havia listener em 9000/9001 nem processo identificado como Studio/main:app; não foi iniciado outro backend. As alterações do backend serão carregadas em sua próxima inicialização normal. O ComfyUI ativo já tem o novo nó.

## Arquivos para uso e rollback

Instruções completas: `E:/Pemara/.agents/skills/pemara-video-production-lead/references/camera-evidence-and-actor-protection.md`.

Templates: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/templates/sequence_camera_contract.template.json` e `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/workflows/upscaling_obrigatorio/dlss5_actor_protected_anchor.template.api.json`. Os exemplos começam pendentes; não registram revisão realizada.

Backups: `BACKUP_MANIFEST.json`, diretório `before/` e `CHANGES.json` neste pacote. Para rollback, comparar o arquivo atual com o hash posterior antes de restaurar a cópia correspondente; preservar novas alterações feitas depois desta atualização. Não apagar mídias ou novas evidências para reverter o código.
