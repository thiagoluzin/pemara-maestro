# Pesquisa - Melhorar Movimento I2V

Data: 2026-07-04

Objetivo: melhorar os vídeos por takes sem usar GPU durante o descanso da placa.

## Diagnóstico Atual

O pipeline melhorou muito em qualidade visual quando passou a gerar imagens-base em anime atual e JSON de validação antes dos takes.

Problema restante:

- pouco movimento real;
- câmera tímida;
- takes contemplativos demais;
- eventos visuais pobres;
- tendência do Wan 5B a transformar keyframe em imagem viva.

## Achados Principais

### Wan2.2

Fontes:

- https://github.com/Wan-Video/Wan2.2
- https://docs.comfy.org/tutorials/video/wan/wan2_2
- https://comfyanonymous.github.io/ComfyUI_examples/wan22/

Conclusão operacional:

- Wan2.2 5B é bom para preview local.
- Wan2.2 A14B com HighNoise + LowNoise deve ser usado em takes aprovados ou quando o 5B congela.
- HighNoise tende a mandar em estrutura/movimento amplo; LowNoise tende a refinar detalhe.
- Para movimentos fortes, o workflow dedicado HighNoise + LowNoise é prioridade técnica.

### LTX-Video

Fontes:

- https://github.com/Lightricks/LTX-Video
- https://github.com/Lightricks/ComfyUI-LTXVideo
- https://comfyanonymous.github.io/ComfyUI_examples/ltxv/

Conclusão operacional:

- LTXV é forte candidato para testar motion quando Wan fica estático.
- LTX exige prompts longos e bem específicos.
- LTXV 13B 0.9.8 distilled pode ser útil para cenas longas e multiscale.
- LTX-2.x parece promissor, mas o próprio ComfyUI-LTXVideo cita 32GB+ VRAM para fluxos LTX-2; na RTX 5080 16GB deve ser tratado como futuro/offload/cloud, não rotina local agora.

### FramePack

Fonte:

- https://github.com/lllyasviel/FramePack

Conclusão operacional:

- Candidato forte para long shots e anti-drift.
- Trabalha com geração progressiva e contexto compactado.
- Não deve substituir o pipeline atual sem instalação isolada e teste próprio.

## Regras Novas

Contrato permanente de continuidade: toda fronteira entre takes exige conector de acao gerado ou
um take unico ininterrupto. Crossfade/xfade, quadro congelado, hold, cauda estatica e reset de
movimento sao proibidos. O conector deve herdar velocidades visiveis do take anterior, executar
uma acao irreversivel e entregar movimento ao take seguinte; `crossfade_frames`, `freeze_frames`
e `static_hold_frames` devem ser zero.
O mesmo contrato vale internamente para todo take gerado, mesmo quando ele nao conecta dois takes.
O movimento util deve ocupar toda a duracao e ser descrito/confirmado nos intervalos `0-30%`,
`30-70%` e `70-100%`. Evento concluido cedo seguido de pose, respiracao ou camera quase parada e
cauda estatica e reprova o take, mesmo quando `freezedetect` nao acusa quadros identicos.
Conectores first/last-frame exigem ancoras extraidas de trechos com movimento visivel antes e
depois do quadro escolhido. Usar a pose final parada ou o primeiro quadro parado de outro take
induz o modelo a sustentar a pose e e bloqueado antes da GPU.

1. Não renderizar vídeo inteiro em prompt único.
2. Não gerar take sem imagem-base aprovada e JSON.
3. Toda transição precisa passar quatro gates visuais: câmera evidente, profundidade real, ação
   interna e progressão clara.
4. Câmera evidente exige deslocamento físico legível (dolly, truck, crane, tracking ou orbit) e
   mudança de perspectiva. Zoom, rack focus, pan/tilt ou tremor isolados não passam.
5. Profundidade real exige primeiro plano, plano médio e fundo, com deslocamento diferencial,
   oclusão ou mudança coerente de escala. Parallax 2D isolado não passa.
6. Ação interna exige evento físico e pelo menos dois elementos movendo-se independentemente da
   câmera. Luz, fumaça ou partículas sozinhas não passam.
7. Progressão clara exige começo, meio e fim diferentes, mudança de estado e saída que motive o
   próximo corte. Reset, reversão gratuita e cauda estática reprovam.
8. Se parecer foto animada, reprovar.
9. Se o Wan 5B congelar, testar:
   - LoRA menor (`0.04` a `0.08`);
   - prompt com evento mais explícito;
   - LTXV como comparativo;
   - Wan2.2 A14B HighNoise + LowNoise para final.

O gate universal é executável em `tools/transition_motion_gate.py`: usar `--stage contract` antes
da GPU e `--stage approval` antes de aprovar ou montar uma transição.

## Backlog Técnico

1. Criar workflow Wan2.2 A14B I2V HighNoise + LowNoise no Studio.
2. Criar executor comparativo: mesmo keyframe em Wan 5B, Wan A14B e LTXV.
3. Criar QC automático com frames primeiro/meio/fim e `qc_motion_probe.py`.
4. Criar preset de prompt "motion beats" no frontend do Studio.
5. Criar regra de bloqueio: preview completo só monta takes aprovados em QC.

## Skill Criada

Skill local:

- `E:/Pemara/.agents/skills/pemara-video-motion-director`

Uso:

- direção de movimento;
- pesquisa de modelos;
- revisão de takes;
- QC;
- planejamento sem usar GPU.

## Janela Especial 2026-07-05

O usuario informou que vai usar o PC durante o dia. A GPU fica liberada apenas:

- inicio: 2026-07-05 17:00;
- fim: 2026-07-06 06:00.

Antes dessa janela, trabalhar somente em pesquisa, docs, prompts, JSON e QC.

Durante a janela, testar primeiro um unico take dificil:

- candidato 1: `05_tenebra`;
- candidato 2: `06_onda_silencio`.

Comparativos planejados:

1. Wan2.2 5B LoRA `0.06`;
2. Wan2.2 A14B HighNoise + LowNoise com offload para RAM;
3. LTXV 13B se sobrar tempo.

Nao rodar lote completo sem validar o primeiro comparativo.

## Atualizacao 2026-07-11 - parar de insistir no caminho fraco

A rodada `four_takes_6s_20260711_0157` confirmou que o problema nao esta resolvido por mais treino
cego no Wan 5B:

- parte dos takes ficou como imagem viva;
- parte moveu, mas com alucinacao e artefato;
- a relacao tempo/GPU por ganho ficou ruim;
- a proxima etapa precisa ser outro workflow base ou controle real de camera.

Nova fonte operacional:

- `docs/08_plano_antiperda_gpu_video_local.md`

Regra nova:

1. Wan 5B I2V fica reprovado como motor de producao local.
2. LoRA de video fica pausado ate o workflow base passar smoke test.
3. Proximo teste local deve priorizar LTX-Video ja instalado, Wan Fun Camera/Fun Control ou FramePack isolado.
4. Nenhuma rota recebe lote/treino antes de passar QC curto com movimento real.
