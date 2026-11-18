# Reinstrumentacao local no Maestro

> O produtor padrao e `stem_producer_v2`: separacao Demucs, transcricao Basic
> Pitch, partes independentes, SoundFont MuseScore e QC por stem. O ACE-Step
> permanece opcional e experimental; o arranjador anterior permanece como
> fallback reversivel `legacy_midi`.

## Objetivo

Transformar um audio que o proprietario tem autorizacao para adaptar em um
novo candidato instrumental, mantendo a linha temporal e uma aproximacao das
notas detectadas. Todo o processamento ocorre no computador local.

O fluxo nao promete transcricao perfeita nem substitui revisao musical. Uma
passagem polifonica densa pode exigir correcao posterior do MIDI.

## Pipeline

1. O upload e salvo em `dados/studio/music_reinstrument/<job>/source/` e recebe
   SHA-256. O original nunca e sobrescrito.
2. FFmpeg cria uma copia PCM de trabalho em 44,1 kHz estereo.
3. Demucs 4 separa `drums`, `bass`, `vocals` e `other`, usando a RTX reservada no
   modo v2 e CPU no modo legado. Um
   adaptador local grava os stems em WAV PCM 24-bit sem depender de TorchCodec.
4. Spotify Basic Pitch 0.4.0 converte os stems melodicos para notas.
5. O `Pemara Stem Producer v2` transforma a direcao em papeis e limites reais:
   uma familia melodica por vez, guitarra com no maximo dois ataques por
   compasso, baixo sustentado e bumbo limitado por compasso.
6. O arranjador escreve MIDI separado para piano, violino, cello, guitarra,
   contrabaixo e bateria; melodia, sustentacao e ritmo nao sao copiados para
   todos os instrumentos.
7. FluidSynth 2.4.7 renderiza cada stem com o MS Basic do MuseScore. FFmpeg
   compensa as diferencas fixas de volume entre os programas desse SoundFont e
   depois aplica uma cadeia especifica de EQ/dinamica e o ganho criativo de cada
   pista antes da soma. O modo legado continua usando GeneralUser GS 2.0.3.
8. Um critico deterministico le integralmente cada WAV, mede audibilidade,
   cobertura, densidade, serra, pulso mecanico e contribuicao na mix.
9. FFmpeg entrega WAV PCM 24-bit/44,1 kHz, preview MP3 320 kbps e os seis stems.
10. O gate final executa decode completo, duracao, sample peak, loudness e
    contagem de amostras clipadas.

A RTX 5090 e usada somente na separacao Demucs sob a reserva cooperativa do
Maestro. Se o ComfyUI estiver produzindo, o job fica enfileirado, invisivel em
`Arquivos` e espera sem interromper a tarefa ativa. O job permanece
`PENDING_HUMAN_REVIEW` mesmo quando todos os gates passam.

## Contrato HTTP

Todas as rotas permanecem sob a fronteira autenticada existente do Studio.

### Consultar runtime

`GET /api/music-reinstrument/status`

Retorna dependencias, versoes, presets, instrumentos, limite de duracao e os
campos invariantes `localOnly=true`,
`humanReviewRequired=true` e `autoApprove=false`.

### Criar job

`POST /api/music-reinstrument/jobs` com `multipart/form-data`:

- `file`: WAV, FLAC, MP3, M4A, AAC, OGG ou Opus;
- `rights_confirmed`: precisa ser `true`;
- `preset`: `symphonic_heavy_metal`, `traditional_heavy_metal`,
  `chamber_metal` ou `piano_strings`;
- `instruments`: lista separada por virgulas;
- `intensity`: `0.35` a `1.0`;
- `keep_vocals`: `true` ou `false`;
- `orchestration_prompt`: direcao livre, com ate 1.500 caracteres.
- `engine`: `stem_producer_v2` (padrao), `ace_step_xl` experimental ou `legacy_midi`;
- `candidate_count`: de 2 a 4 no fluxo neural;
- `cover_strength`: de `0.3` a `0.9` no fluxo neural.

Exemplo de direcao:

```text
Piano e violino carregando a melodia em primeiro plano; cello forte e
expressivo; contrabaixo e bateria bem presentes; guitarra apenas como base
ritmica discreta, sem encobrir os outros instrumentos.
```

O texto nao sai da maquina. Em `stem_producer_v2`, ele controla papeis, ataques,
duracoes, densidade e ganho das pistas. Em `ace_step_xl`, orienta uma mix neural
completa e o Studio gera de dois a quatro candidatos. Em `legacy_midi`, o
orquestrador anterior reconhece os seis instrumentos e expressoes como
`principal`, `forte`, `presente`, `apoio`, `discreto` e `sem guitarra`.

Resposta `202`:

```json
{
  "ok": true,
  "jobId": "...",
  "status": "queued",
  "humanReviewRequired": true,
  "autoApprove": false
}
```

### Acompanhar, cancelar e baixar

- `GET /api/music-reinstrument/jobs/{jobId}`
- `GET /api/music-reinstrument/jobs?page=1&page_size=20`
- `POST /api/music-reinstrument/jobs/{jobId}/cancel`
- `GET /api/music-reinstrument/jobs/{jobId}/artifacts/{artifactKey}`

Os caminhos absolutos do servidor nunca aparecem na resposta publica. Os
artefatos sao resolvidos por chave e confinados ao diretorio do proprio job.

### Revisao humana

`POST /api/music-reinstrument/jobs/{jobId}/review`

```json
{ "decision": "APPROVED", "reason": "", "candidateIndex": 2 }
```

ou

```json
{ "decision": "REJECTED", "reason": "motivo obrigatorio", "candidateIndex": 2 }
```

Aprovacao marca somente aquele master como `OWNER_APPROVED_FINAL`, sem novo
render. Rejeicao preserva o candidato para rollback e bloqueia sua promocao.

## Biblioteca Arquivos

O master WAV de um job concluido aparece automaticamente na sessao `Arquivos`,
sem copiar ou alterar o original. Candidatos pendentes recebem o rotulo
`Aguardando sua escuta`; o master exato aprovado recebe `Master aprovado`.
Candidatos rejeitados continuam preservados no job para rollback, mas saem da
biblioteca ativa.

## Instalacao e recuperacao

O runtime fica isolado em
`ferramentas/audio_neural/reinstrument_runtime/`. Para reconstruir:

```powershell
powershell -ExecutionPolicy Bypass -File tools\install_music_reinstrument_runtime.ps1
```

O runtime neural fica em `ferramentas/audio_neural/music_ai_runtime/`. A
reconstrucao idempotente, com revisoes fixas e prova opcional, usa:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ferramentas\audio_neural\music_ai_runtime\install_music_ai.ps1 -RunSmoke
```

O instalador fixa versoes e hashes do FluidSynth e do SoundFont, valida FFmpeg,
Demucs 4.0.1 e deixa o checkpoint `htdemucs` em cache. Os binarios, pesos e o
ambiente virtual nao entram no Git.

## Limites conhecidos

- O ACE-Step condiciona a producao pela faixa e pelo prompt, mas nao oferece
  stems isolados nem garante que todo instrumento pedido apareca com o balanco
  desejado. O lote e o critico reduzem esse risco; somente a escuta decide.
- O critico MuQ usa pesos CC-BY-NC 4.0. O fluxo neural atual e, portanto,
  restrito a testes, pesquisa e uso nao comercial.

- Basic Pitch funciona melhor em um instrumento por vez; a separacao previa
  reduz, mas nao elimina, erros de nota.
- O arranjo automatico preserva a linha temporal e material detectado, mas nao
  reconstrui articulacao humana ou mix de estudio com perfeicao.
- O prompt controla papeis, densidades, intensidades e ganhos; ele nao entende
  qualquer frase como um modelo generativo aberto. A interface exibe o plano
  resultante para evitar que uma interpretacao silenciosa passe despercebida.
- MS Basic e adequado para candidato e estudo. Uma entrega comercial de alto
  nivel pode substituir o SoundFont por VSTs licenciados, reutilizando os MIDIs
  e stems separados.
- Confirmar direitos no formulario e um gate operacional, nao uma verificacao
  juridica automatica.
