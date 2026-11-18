# ACE-Step experimental do Maestro

## Resultado entregue

Este e o modo experimental opcional. O modo padrao do Studio e o produtor por
stems v2, documentado em `docs/MUSIC_REINSTRUMENTATION.md`.

O ACE-Step usa o audio autorizado como condicionamento estrutural, cria de dois
a quatro arranjos completos e os apresenta lado a lado. O fluxo foi desenhado
para evitar que uma unica guitarra seja aceita apenas porque o arquivo e
tecnicamente valido: cada candidato passa por QC objetivo e por um critico
neural que avalia musicalidade, aderencia ao prompt e semelhanca estrutural.
O MuQ-MuLan tambem registra afinidades auditivas separadas para baixo, bateria,
piano, cordas e `guitar wall`, facilitando identificar candidatos em que a
guitarra voltou a mascarar o conjunto. Esses valores sao comparativos, nao
medicoes em decibeis nem prova de que um instrumento esta presente.

Uma classificacao tecnica nunca e aprovacao. Todos os candidatos terminam em
`PENDING_HUMAN_REVIEW`; somente a decisao do proprietario muda o candidato
exato para `OWNER_APPROVED_FINAL` ou `OWNER_REJECTED`.

## Arquitetura

```text
upload autorizado
  -> validacao FFprobe (10 s a 10 min)
  -> original preservado e identificado por SHA-256
  -> reserva cooperativa da RTX 5090
  -> ACE-Step 1.5 XL Base, tarefa cover, 2-4 candidatos
  -> bruto FLAC preservado
  -> master gain-only WAV PCM 24-bit/48 kHz + preview MP3 320 kbps
  -> decode integral, duracao, loudness, pico e clipping
  -> MuQ-Eval A1 + MuQ-MuLan + comparacao de melodia/ritmo
  -> ranking explicavel
  -> Arquivos + player + decisao humana por candidato
```

O ranking combina proxies de impressao, aderencia relativa, estrutura e
balanco. Candidato que falha o gate tecnico recebe penalidade eliminatoria.
Essa formula apenas ordena a escuta; ela nao entende orquestracao nem prova
qualidade artistica, originalidade ou direitos.

## Como dirigir o arranjo

Escreva papeis e relacoes de mix, nao somente uma lista de instrumentos. Um
prompt inicial util e:

```text
Piano e violino conduzem a melodia em primeiro plano. Cello forte e lirico.
Baixo eletrico e bateria acustica de metal claramente audiveis durante toda a
faixa. Guitarra tradicional agressiva apenas como base ritmica, sem mascarar
piano, cordas, baixo ou bateria. Arranjo coerente, com espaco e sem parede de som.
```

- `Fidelidade 0,55` e o ponto inicial equilibrado.
- Valores maiores preservam mais a influencia da faixa de origem.
- Valores menores permitem uma reinterpretacao mais ampla.
- Tres candidatos sao recomendados para uma comparacao normal; quatro aumentam
  tempo e memoria, mas oferecem mais escolha.
- Se baixo ou bateria estiverem fracos, descreva `claramente audivel durante
  toda a faixa` e diga explicitamente qual instrumento nao pode mascara-los.

O ACE-Step gera uma mixagem completa, nao stems independentes. Mesmo com um
prompt preciso, um candidato pode ignorar ou enfraquecer um instrumento. Por
isso o Studio gera um lote e preserva cada bruto; ele nao tenta ocultar essa
limitacao com uma nota automatica.

## Artefatos de cada sessao

- original intacto em `source/`;
- FLAC bruto de cada candidato em `raw/`;
- WAV PCM 24-bit/48 kHz e MP3 320 kbps por candidato;
- relatorio de geracao ACE-Step;
- relatorio do critico MuQ;
- relatorio de producao com formula, seeds, hashes e QC;
- ZIP de revisao sem duplicar os aliases do candidato recomendado;
- logs separados para geracao, master, preview e critica.

O master recebe somente ganho linear limitado para comparacao, com o bruto
preservado. Nao ha compressao, limitacao destrutiva ou substituicao silenciosa.

## Operacao e GPU

O worker adquire `dados/studio/gpu_lease.json`, espera outro produtor terminar
e nunca encerra processos alheios. Antes de carregar o ACE-Step, confirma que a
fila do ComfyUI esta vazia e pede apenas a liberacao de alocacoes ociosas. A
reserva e liberada em sucesso, erro ou cancelamento.

O ACE-Step e o critico rodam em subprocessos isolados, com argumentos em lista,
timeout, log e cancelamento do processo pertencente ao job. O critico usa o
cache local em modo offline e revisoes exatas, impedindo troca silenciosa de
peso durante uma producao.

## Instalacao reproduzivel

```powershell
# Apenas mostra o plano; nao altera nada
powershell -NoProfile -ExecutionPolicy Bypass -File ferramentas\audio_neural\music_ai_runtime\install_music_ai.ps1 -DryRun

# Instala/revalida e executa prova sintetica de gerador + critico
powershell -NoProfile -ExecutionPolicy Bypass -File ferramentas\audio_neural\music_ai_runtime\install_music_ai.ps1 -RunSmoke
```

O instalador fixa commits de ACE-Step, MuQ e MuQ-Eval, usa o `uv.lock` oficial
do ACE-Step, sincroniza o ambiente do critico por lock local e baixa snapshots
por SHA. Ele falha se encontrar um checkout existente em outra revisao; nenhum
`reset` automatico e feito.

Os pesos ACE ficam em
`ferramentas/audio_neural/music_ai_runtime/models/ace_step`. O cache compartilhado
do Hugging Face fica por padrao em `D:\PemaraAI\huggingface-home\hub`. O recibo
final e `ferramentas/audio_neural/music_ai_runtime/installation_receipt.json`.
O instalador tambem direciona o cache do `uv` para `D:\PemaraAI\uv-cache`,
evitando duplicar pacotes grandes dentro do projeto ou no disco do sistema.

## API

- `GET /api/music-reinstrument/status`
- `POST /api/music-reinstrument/jobs`
- `GET /api/music-reinstrument/jobs/{jobId}`
- `POST /api/music-reinstrument/jobs/{jobId}/cancel`
- `GET /api/music-reinstrument/jobs/{jobId}/artifacts/{artifactKey}`
- `POST /api/music-reinstrument/jobs/{jobId}/review`

Campos adicionais do produtor neural: `engine=ace_step_xl`,
`candidate_count=2..4` e `cover_strength=0.3..0.9`. A revisao recebe
`candidateIndex`; campos desconhecidos sao rejeitados.

## Licencas e limite de uso

O codigo ACE-Step 1.5 e os pesos usados pelo gerador estao sob MIT. O codigo de
MuQ/MuQ-Eval e aberto, mas os pesos MuQ e MuQ-MuLan selecionados usam
CC-BY-NC 4.0. Enquanto esse critico fizer parte obrigatoria do pipeline, a
entrega e restrita a estudo, pesquisa e uso nao comercial. Remover o critico ou
trocar pesos exige uma revisao separada de arquitetura, qualidade e licenca.
