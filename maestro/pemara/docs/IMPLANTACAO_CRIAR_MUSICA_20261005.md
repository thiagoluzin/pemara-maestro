# Criar música no Maestro — 5 de outubro de 2026

## Entrega

- ACE-Step 1.5 e YuE2 incluídos no seletor de Criar música. LeVo 2 permanece disponível.
- Controles de letra/instrumental; ACE Turbo/XL Base e BPM; planejamento ABC e geração YuE2 separados, com confirmação explícita da partitura.
- Histórico persistente com player, botão Ouvir no painel, download, repetição e revisão de partitura.
- Reserva cooperativa da GPU para os novos motores. O subprocesso ACE assume a reserva enquanto executa; cancelamento encerra apenas seu próprio processo.
- Nenhum fallback de motor desconhecido para ElevenLabs Music. Não há chamadas pagas nos novos caminhos.

## Atualização isolada

Fonte oficial ACE-Step: `ca1e85fe9430179831e6bc6be790c332190a3866`, em `ferramentas/audio_neural/music_ai_runtime/sources/ACE-Step-1.5-20261005`, com venv independente criada pelo lock oficial. Os pesos existentes são compartilhados, com downloads de modelos desativados no worker. Fonte, ambiente, recibo e integração de reinstrumentação antigos foram preservados.

Backup dos arquivos anteriormente modificados: `backups/music_create_20261005_085221`.

O torchao emite aviso sobre extensões C++ incompatíveis com Torch 2.7.1. A criação usa `quantization=None`; importação e inferência Turbo passaram. Não se declara funcionamento da quantização.

## Evidências

- Oito testes de criação musical passaram: transporte multipart de letra/modelo, separação de grafos, revisão obrigatória, persistência, ausência de fallback, reserva/liberação da GPU e cancelamento.
- Onze testes da persistência de trabalhos passaram.
- Compilação Python e sintaxe JavaScript passaram.
- Validação MCP dos grafos YuE2 de planejamento e geração: ambos válidos, sem erros, avisos ou nós pagos. A inferência YuE2 atual não foi executada nesta entrega; o smoke anterior não qualifica automaticamente a versão atual.
- ACE Turbo: áudio instrumental de 10 s e faixa vocal de 180 s gerados na instalação nova. XL Base está instalado e conectado, mas não teve smoke de criação original nesta entrega.
- Suite ampla de controle/persistência: 127 de 129 passaram. As duas falhas chamam `asyncio.run` em `generative_queue`, que já era síncrona no backup anterior à alteração; não são tratadas como validação verde nem corrigidas fora do escopo.
- Studio reiniciado pelo supervisor Radar; API confirma os dois novos providers. Build publicado: `20261005-local-music-create-v2`.
- Endpoint da faixa atende Range com HTTP 206 e conteúdo FLAC.

## Música solicitada pelo proprietário

**Midnight Masquerade**, 180 s, estéreo 48 kHz, ACE-Step Turbo, seed `202610051`. Direção: rock teatral pesado inspirado na energia de Herald of Darkness, com letra e melodia novas; tempo solicitado 156 BPM. Esse tempo é uma escolha de direção apoiada em metadados/arranjo publicados, não uma medição da gravação original nem uma confirmação do tempo realizado pelo modelo.

Referência oficial consultada: [Herald of Darkness — vídeo oficial](https://www.youtube.com/watch?v=uxs_HYw_mLk). Apoio de andamento: [arranjo publicado, aproximadamente 155 BPM](https://www.musicnotes.com/sheetmusic/atinpiano/herald-of-darkness/MN0293517), [metadados da versão instrumental, 156 BPM](https://trackify.am/track/6SHwW9L9YBNjLTVs2htnC4/tempo). Não se afirma identidade de riffs, mix, melodia ou voz com a referência sem escuta comparativa.

Job: `music-midnight-masquerade-20261005-attempt01`.

Arquivo, letra, spec, recibo e QC: `outputs/music_midnight_masquerade_20261005`. Estado: `PENDING_HUMAN_REVIEW`. QC técnico confirma duração, amostras finitas e energia nos seis intervalos; não comprova similaridade estilística, letra cantada correta ou aprovação artística.

O usuário pode ouvir em **Criar → Trabalhos recentes → Midnight Masquerade → Ouvir no painel**.
