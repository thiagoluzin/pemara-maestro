# Instrumentos amostrados locais do Maestro

Este runtime separa duas responsabilidades:

- MuScriptor/Basic Pitch/Beat This analisam o audio e constroem a partitura.
- sfizz toca a partitura com gravacoes multisample de instrumentos reais.

O Maestro nao pode substituir automaticamente estes bancos por General MIDI.
Piano, violino, cello, baixo e bateria precisam estar presentes para a
orquestracao; se algum estiver ausente, a execucao deve ser bloqueada.

Os patches `Pemara-*` sao derivados locais. Eles preservam os originais e
desligam a desafinacao aleatoria das cordas. O patch de bateria apenas adapta o
crash GM 49 ao mapa do SM Drums sem alterar as notas do MIDI.

Para recriar os patches depois de reinstalar as bibliotecas:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\prepare_sampled_patches.ps1
```

O `runtime_manifest.json` registra versoes, fontes, licencas e hashes dos
arquivos baixados. MuseHub/Muse Sounds pode ser usado futuramente como rota
opcional, mas exige login humano e nao e fallback silencioso deste runtime.

## Interpretacao expressiva do Partitura Primeiro

O perfil `expressive_score_v1` e a etapa padrao dos novos renders de partituras
ja aprovadas. O arquivo canonico e o arranjo base ficam intactos. A interpretacao
tem seu proprio MIDI, plano JSON, vozes e patches derivados dentro de
`outputs/score_first_orchestration_<tentativa>/performance/`.

- Acordes de cordas sao separados em vozes monofonicas, sem cortar notas.
- Notas fora do registro do violino vao ao cello, na mesma altura, somente
  quando o cello ja foi solicitado. Caso contrario a execucao e bloqueada.
- A envoltoria RMS do original, suavizada em 2,25 segundos, coordena as curvas
  de expressao CC11. Nao ha desafinacao ou deslocamento aleatorio das notas.
- CC20 escolhe sustain ou staccato gravado; CC1 regula o ataque do arco.
- As caudas de sustain ficam em 120 ms (violino) e 140 ms (cello). As camadas
  de ruido de release e o vibrato sintetico adicional sao removidos apenas dos
  patches derivados. Afinacao corretiva das amostras originais e preservada.
- Cada voz tem render separado, evitando conflito entre controles MIDI. As
  cordas recebem posicoes de palco, enquanto baixo e bateria tem um reforco
  moderado e explicitamente registrado no relatorio.
- O master usa duas passagens de loudness, alvo de -13 LUFS e -1 dBTP, sem
  ganho automatico oculto do limiter. O arquivo cobre o fim da partitura mais
  uma cauda, mesmo quando isso ultrapassa a duracao do audio de referencia.
  Uma mensagem terminal CC123 mantem essa cauda no render do sfizz; apenas
  atrasar o evento MIDI End Of Track nao e suficiente nesse renderizador.

Isto e um interpretador baseado em regras e medidas, nao uma nova IA musical.
VPO nao tem gravacoes de transicao legato entre todos os intervalos; ajustar
envelopes nao cria essas gravacoes. Nenhum teste tecnico aprova naturalidade,
arranjo ou gosto musical. Bibliotecas comerciais nao foram adquiridas.

### Verificacao e rollback

Em `services/studio`, executar:

```powershell
python -m unittest test_music_reinstrument test_music_score_first test_music_performance_mix test_music_ai_api
```

Em `ferramentas/audio_neural/muscriptor_runtime`, executar:

```powershell
.\venv\Scripts\python.exe -m unittest test_expressive_performance -v
```

O segundo conjunto inclui um teste que renderiza audio real e mede se CC11
altera o violino, se staccato produz som e se a cauda inteira e renderizada. Os contratos
comparam altura, ataque, duracao e velocidade de cada nota, incluindo duplicatas.

`tools/render_expressive_score_candidate.py` recebe um job e um rotulo novo.
Sem `--execute`, faz somente a verificacao inicial. Com execucao, exige o hash
da aprovacao humana da partitura, salva o estado anterior em `reviews/` e mantem
a rejeicao anterior em `preservedCandidates`. Artefatos existentes nunca sao
sobrescritos. O novo master continua `PENDING_HUMAN_REVIEW` quando passa no gate.

Para uma comparacao tecnica explicita com o renderer antigo, o chamador local
pode usar `LockedScoreOrchestrationRequest(expressive_performance=False, ...)`
com outro rotulo. Nao ha retorno silencioso ao modo antigo. Recarregar o Studio
somente quando tanto ComfyUI quanto os jobs do Studio estiverem ociosos.
