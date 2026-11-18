# Video Global Engine - Pemara

## Onde ficam os vídeos prontos

Os vídeos aprovados ficam centralizados em:

`E:\Pemara\maestro\pemara\ferramentas\video_global_engine\PRONTOS`

Cada projeto tem uma pasta própria, com:

- `takes_aprovados`: somente takes com status Maestro `APPROVED` ou `FINAL`;
- `masters`: montagens finais que passaram pela validação técnica e visual;
- `STATUS.md`: resumo do que está disponível.

Os arquivos nessa pasta são hardlinks sempre que possível: abrem como arquivos normais,
sem duplicar o espaço ocupado pelo vídeo original. Nenhum original é movido ou apagado.

A pasta é atualizada automaticamente quando o status de um take é alterado no Maestro.
Para atualizar manualmente após criar um master fora desse fluxo:

```powershell
python E:\Pemara\maestro\pemara\services\studio\ready_exports.py --projects-root E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos
```

Motor oficial para criar videos profissionais por metodologia de takes.

## Regra principal

Video profissional nao nasce de prompt unico longo.

O fluxo oficial e:

```text
ideia -> roteiro -> take_queue -> imagens-base -> videos curtos -> QC -> montagem -> dataset de treino
```

Prompt unico longo fica permitido apenas como rascunho conceitual.

## Regra inquebravel de JSON

Sem JSON = ativo invalido.

Todo asset que entra no motor precisa de rastreabilidade antes de avançar:

- imagem-base precisa de `.json` lateral com prompt, modelo, seed/dimensoes quando houver,
  status de validacao e checklist de QC;
- imagem-base sem `.json` lateral nao pode virar take;
- take MP4 gerado precisa de `.json` lateral com imagem-base usada, JSON da imagem-base, prompt de
  animacao, modelo, LoRA, parametros e QC pendente;
- montagem parcial/final precisa de `.json` lateral listando os takes e seus JSONs.

O executor da intro bloqueia a geracao se a imagem-base nao tiver JSON lateral aprovado. Para auditar
um projeto por takes, use:

```powershell
python E:\Pemara\maestro\pemara\ferramentas\video_global_engine\tools\enforce_take_image_json.py --project E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\intro_ritmos_revolta
```

## Objetivo

Transformar uma ideia simples do usuario em uma linha de producao:

1. entender objetivo, publico, duracao e estilo;
2. quebrar a narrativa em takes de 5s a 12s;
3. criar imagens-base aprovaveis;
4. animar cada take separadamente;
5. rejeitar e refazer apenas takes ruins;
6. montar o MP4 final com audio, cortes e branding;
7. salvar aprovados como dataset para treinos futuros.

## Formula de modelos

Pesquisa operacional atualizada:

- `docs/04_pesquisa_movimento_i2v.md`
- `docs/05_pesquisa_comunidade_animacao_video_20260705.md`
- `docs/06_estudio_animacao_profissional.md`
- `docs/07_rotina_noturna_estudio_local.md`
- `docs/08_plano_antiperda_gpu_video_local.md`
- `docs/09_metodo_veo_kling_para_motor_local.md`
- `docs/10_pesquisa_comunidade_modelos_video_imagem_20260714.md`

Registro operacional:

- `templates/studio_video_model_registry.json`: modelos locais, LoRAs prontas candidatas e ordem de teste do estudio.
- `install_ready_video_loras.ps1`: instalador controlado para baixar LoRAs prontas especificas no ComfyUI.
- `run_nightly_local_studio.ps1`: orquestrador noturno de testes locais.
- `restore_sprunki_gpu_tasks.ps1`: restaura tasks Sprunki/treino pausadas durante prioridade do estudio.

`Ritmos da Revolta` e apenas bancada de teste. O objetivo final e um estudio global de animacoes profissionais.

### Imagem-base

- `Qwen Image`: texto, layout, card, logo, composicao grafica e correcao pontual.
- `HiDream-O1 Image`: geracao de imagem com escolha explicita no Maestro.

Em 15/11/2026 o proprietario removeu LLaDA Base/Turbo, Z-Image Base/Turbo,
todos os Flux e HunyuanVideo 1.5. Essas opcoes sairam dos seletores; workflows
antigos que usam esses pesos ficam bloqueados antes da fila, sem troca de motor.
Projetos, midias, LoRAs de treinamento e grafos historicos permanecem preservados.

### Video

- `MiniMax H3 FL2VA pruned INT8 ConvRot`: unico motor autorizado para takes e conectores.
- `Qwen3-VL-32B MiniMax H3 NVFP4 AWQ`: encoder textual e multimodal do H3.
- `RIFE 4.6 + RealESRGAN x2plus + H.264 NVENC`: acabamento somente depois da aprovacao visual.
- `HunyuanVideo-Foley XXL`: Foley somente depois do picture lock e sempre pendente de escuta humana.

Contrato atual: `docs/decisions/ADR-004-minimax-h3-workflow-unico.md`. As pesquisas Wan/LTX
abaixo permanecem apenas como historico e nao autorizam esses motores.

Regra 2026-07-11: o fluxo local `Wan 5B I2V + LoRA + mais treino` esta congelado para producao
ate um novo workflow base passar no gate curto de movimento. Video local fica em laboratorio, nao
em lote cego.

Metodo 2026-07-11: copiar o formato Veo/Kling: start frame, end frame, referencias visuais,
shot contract, camera nomeada, variantes curtas, QC e montagem. Ver
`docs/09_metodo_veo_kling_para_motor_local.md`.

Pesquisa 2026-07-14: o estudio agora trata video e imagem como familias de capacidades, nao como
um LoRA unico. Ver `docs/10_pesquisa_comunidade_modelos_video_imagem_20260714.md` para a matriz
de modelos, ferramentas comunitarias e golden sets de avaliacao.

### Apoio

- NVIDIA NIM: analisar logs, revisar prompts, comparar previews e gerar relatorios de treino/QC.
- FFmpeg: montagem, cortes, fps, audio e loudness.

## Bridge editorial Unimedia (opt-in)

O Maestro pode receber `FactPack`, plano de cenas, briefs de arte/movimento, custo, overlays e
proveniencia de um run do Unimedia por um bridge local fail-closed. Ele nao copia codigo do
repositorio, nao inicia GPU/audio e nao sobrescreve projetos. Cada cena vira take `PLANNED`, com
LTX/Gemma/RIFE vigente e imagem-base ainda pendente de aprovacao humana. O bridge `v1_1` preserva
um manifesto SHA-256 do import e recusa repeticoes corrompidas ou com aprovacao divergente.

Primeiro, emita a revisao vinculada por SHA-256:

```powershell
python tools/unimedia_editorial_bridge.py E:\caminho\run --review-dir E:\Pemara\scratch\unimedia_maestro_bridge\run
```

Somente depois de corrigir bloqueios, revisar o manifest e registrar autorizacao escrita:

```powershell
python tools/unimedia_editorial_bridge.py E:\caminho\run --review-dir E:\Pemara\scratch\unimedia_maestro_bridge\run --apply
```

Contrato completo, exemplos, gates de direitos e rollback:
`docs/12_unimedia_editorial_bridge.md`. Decisao arquitetural:
`docs/decisions/ADR-003-unimedia-editorial-bridge.md`. Correcoes verificadas: `FIXLOG.md`.

## Estrutura de projeto

Cada projeto deve seguir:

```text
projetos/nome_do_projeto/
  project_manifest.json
  take_queue.json
  assets/
  base_images/
  takes/
  qc/
  output/
  training_exports/
```

## Regra de duracao

- take comum: `8s`;
- take curto/transicao: `5s`;
- take de abertura: `10s`;
- take de climax/final: `12s`;
- evitar take acima de `12s` salvo caso especial.

## Regra de qualidade

Todo take precisa ter:

- imagem-base aprovada;
- prompt de animacao;
- proibicoes explicitas;
- movimento obrigatorio por camada;
- contact sheet;
- frame inicial, meio e final;
- status `approved`, `rejected` ou `needs_retry`;
- motivo claro se reprovado.

## Regra de movimento cinematografico

Esta regra e universal e inquebravel para **todas as transicoes**, independentemente do projeto,
modelo, workflow ou imagem-ancora. Se qualquer pilar abaixo faltar, o take esta reprovado e nao
pode consumir GPU de producao, entrar em montagem nem receber status `approved`.

### Contrato inquebravel de acao continua

O contrato vale para todo take gerado, inclusive planos internos que nao sao conectores. Um take
nao pode concentrar o evento no inicio e usar o restante como pose sustentada, respiracao, brilho
ou camera quase parada.

Toda fronteira entre takes deve ser resolvida por um conector de acao gerado ou permanecer dentro
de um unico take ininterrupto. Crossfade/xfade, quadro congelado, hold, cauda estatica e reset de
movimento sao proibidos, inclusive quando escondidos por flash, fumaca, camera whip ou oclusao.

Um conector valido deve:

1. herdar do take anterior velocidades visiveis de corpos, objetos, efeitos e camera;
2. executar uma unica acao fisica irreversivel, sem voltar a guarda ou reiniciar golpe;
3. terminar ainda em movimento, entregando direcao e consequencia ao take seguinte;
4. ocupar toda a duracao com movimento util, declarando movimento proprio em `0-30%`, `30-70%`
   e `70-100%`; concluir a acao cedo e sustentar pose no restante reprova o take;
5. usar ancoras de transicao retiradas de trechos com movimento visivel antes e depois; a ultima
   pose parada de um take e o primeiro quadro parado do seguinte sao ancoras proibidas;
6. declarar `crossfade_frames=0`, `freeze_frames=0` e `static_hold_frames=0`;
7. passar o QC humano com `continuous_action`, `motion_across_all_intervals`,
   `moving_anchor_context`, `no_crossfade`,
   `no_freeze`, `no_static_tail` e `no_reset` verdadeiros.

Um MP4 tecnicamente valido que interrompe a acao para transicionar esta reprovado. O gate falha
fechado quando o contrato acima nao existe.

O preflight do Maestro aplica o mesmo bloqueio antes de criar o job de GPU quando o projeto declara
`continuous_action_contract.required=true`.

Os quatro pilares obrigatorios sao:

1. **Camera evidente:** deslocamento fisico legivel de camera, como dolly, truck, crane, tracking
   ou orbit. Zoom digital, rack focus, pan/tilt ou tremor isolados nao bastam. O enquadramento deve
   mudar por perspectiva, nao apenas por escala 2D.
2. **Profundidade real:** primeiro plano, plano medio e fundo identificaveis, com velocidades
   relativas, mudanca de sobreposicao, oclusao ou escala coerentes com o deslocamento. Filtro de
   parallax 2D nao conta como profundidade.
3. **Acao interna:** pelo menos um evento fisico legivel e dois elementos da cena movendo-se de
   forma independente da camera. Luz, fumaca e particulas podem apoiar a acao, mas nao substitui-la.
4. **Progressao clara:** inicio, meio e fim visualmente distintos; o estado final deve resultar do
   evento e preparar um corte seco, impacto musical ou saida direcional para o take seguinte. Nao
   pode haver reset, reversao gratuita ou cauda estatica.

Antes de gerar, validar o contrato:

```powershell
python tools/transition_motion_gate.py caminho/production_manifest.json --stage contract
```

Antes de aprovar ou montar, validar o QC visual dos quatro pilares:

```powershell
python tools/transition_motion_gate.py caminho/production_manifest.json --stage approval
```

Se o take parecer imagem viva, respirar pouco, depender de zoom/flash, apenas simular parallax ou
parar a acao para trocar de take, ele esta reprovado.

Quando a GPU estiver em descanso, trabalhar apenas em pesquisa, prompts, JSON, QC e documentacao.

## Quando usar video inteiro

Somente para:

- rascunho rapido;
- teste grosseiro de ideia;
- cena simples sem identidade importante.

Nunca usar como fluxo final para video profissional.
