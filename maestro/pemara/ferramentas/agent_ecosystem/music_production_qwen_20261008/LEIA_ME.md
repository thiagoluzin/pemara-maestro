# Produção musical com Qwen 3.8 — implantação em 08/10/2026

Atualização posterior: [correção dos instrumentos, energia e pistas ausentes no Qwen](CORRECAO_INSTRUMENTOS_QWEN.md), com 127 testes passando e confirmação na nova tentativa enviada pelo proprietário.

O Maestro ganhou um contrato comum de produção musical, `pemara.qwen-music-production.v1`. O Qwen local coordena letra, estilo, duração, BPM, seções, função e dinâmica dos instrumentos. Escolhas explícitas do proprietário prevalecem: letra fornecida, duração manual, instrumental/vocal e motor não podem ser substituídos pelo planejamento.

## Comportamento implantado

- Criação automática: planejamento validado para YuE2, ACE e LeVo; duração escolhida pelo Qwen quando a opção está ligada. O YuE2 mantém seu encerramento natural dentro do limite, sem prometer duração exata.
- Reinstrumentação: Qwen habilitado por padrão, preservando o hash da fonte e sua duração. Seções sem análise musical real são identificadas como propostas, não como estrutura medida da gravação.
- Score-first: partitura candidata precisa de revisão e trava por hash antes da orquestração. Voz isolada fornecida ou separada é preservada como arquivo e também precisa de revisão. Duração compatível não comprova sincronismo, ausência de vazamento ou naturalidade.
- Arranjo e mixagem: funções dos instrumentos e mudanças suaves por seção; automação instrumental não altera a faixa vocal. Guitarra elétrica amostrada FreePats Direct, com saturação/EQ declaradas. Não é um amplificador capturado nem comprovação de palm mute realista.
- Entrega: fonte nativa preservada; WAV e MP3 efetivamente medidos. Decode, duração, amostras inválidas, clipping e true peak fazem parte dos gates. Candidatos reprovados não podem ser recomendados/aprovados como master técnico.
- Comparação: cópias de referência e candidato com volume próximo, sem substituir os originais. Letra, voz, melodia, arranjo, timbres, mixagem e finalização continuam sujeitos à escuta do proprietário.
- Interface: controles do Qwen, upload opcional da voz, player da voz preservada, comparação e links do master/original/plano.

Quatro skills e seus perfis foram registrados em `E:\Pemara\.agents\skills`: `pemara-music-production-lead`, `pemara-music-arranger`, `pemara-music-mix-engineer` e `pemara-music-listening-qc`. São responsabilidades de produção; isso não cria subagentes automaticamente.

## Evidência de validação

- 115 testes de backend musical passaram; seis testes da interface passaram.
- JavaScript e módulos Python foram conferidos sintaticamente.
- Render real de guitarra em CPU passou sem clipping/amostras inválidas: `guitar_qualification.json`.
- Fluxo completo em CPU com MIDI e voz de teste sintéticos passou: importação, trava de revisão simulada somente na fixture, plano por seções, orquestração, master WAV, MP3 e comparação. Fonte/voz conservaram seus hashes: `score_roundtrip_verification.json`.
- Grafos YuE2 de planejamento e geração foram validados pelo MCP sem erros/avisos; não foram enviados para gerar música. JSONs de grafos: `yue_plan_validation.json` e `yue_generate_validation.json`.
- Backend implantado respondeu HTTP 200 autenticado e confirmou o contrato, Qwen padrão e guitarra pronta: `deployment_verification.json`. Disponibilidade/configuração não comprova inferência nem qualidade artística.
- O estado final de inferência real do Qwen consta em `implementation_receipt.json`; fixtures determinísticas não são apresentadas como resposta do modelo.

## Piloto e qualificação ainda necessários

O proprietário escolheu **“Admirável Gado Novo” para heavy metal**, em lugar do exemplo sertanejo. Informou que a gravação está em outro PC e chamará quando trouxer o arquivo. Nenhuma versão foi presumida, letra copiada, gravação baixada ou piloto gerado. O teste real depende desse arquivo e da revisão da voz/partitura resultantes.

Não há garantia de fidelidade automática de 100%. A aprovação de uma partitura bloqueada conserva suas notas; não comprova que a transcrição automática reproduziu integralmente a gravação. A qualidade da separação Demucs, timbre metal e equilíbrio real ainda precisam do piloto e de escuta.

RoFormer/MSST como separadores concorrentes, ACE `lego/complete` e modelos de amplificador são extensões do plano de pesquisa que ainda exigem integração/qualificação. Não foram apresentados como instalados ou aprovados nesta implantação.

## Preservação e reversão

Os arquivos existentes copiados antes das mudanças principais ficam em `E:\Pemara\maestro\pemara\backups\music_production_qwen_20261008`; `baseline.json` registra 18 hashes anteriores. Há uma cópia adicional do teste de API. O teste de escolha de duração foi ajustado sem baseline inicial registrado; os novos módulos e quatro skills são novos, não possuem uma versão prévia neste backup.

`routing_before` conserva as rotas anteriores. `skill_changes.json` registra a última execução idempotente do instalador, portanto seus hashes “before” das skills novas não representam o estado anterior ao início do trabalho. `implementation_receipt.json` registra o inventário final e hashes, sem credenciais.

O checkout já continha mudanças de outros trabalhos. Não foi feito reset, commit amplo ou migração de músicas históricas. A ativação usa o supervisor oficial Radar somente para o Studio, após conferir seus jobs e sua lease; trabalhos externos do ComfyUI permanecem preservados.

Referência da guitarra e licença: [FreePats Electric Guitar](https://freepats.zenvoid.org/ElectricGuitar/clean-electric-guitar.html), banco Direct de 2022-09-11, CC0. O recibo registra hashes do arquivo e do patch instalado.
