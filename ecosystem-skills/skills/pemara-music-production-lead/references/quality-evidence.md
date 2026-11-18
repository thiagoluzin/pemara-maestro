# Evidência de qualidade musical

Contrato dos agentes e skills, atualizado após a rejeição de 2026-11-10: composição repetitiva, vocal ruim e falhas no áudio. Os arquivos rejeitados foram apagados por ordem do proprietário; não recriar o lote para testar estas instruções. Este documento orienta o trabalho dos agentes; não representa um gate já implantado no backend Maestro.

## O que cada fase comprova

| Dimensão | Evidência suficiente para revisar | O que não comprova |
|---|---|---|
| Composição | Letra revisada, motivo, hook, intenção e forma desenvolvidos | Título diferente, seed novo ou lista de adjetivos |
| Realização musical | Áudio ouvido com intervalos registrados e comparação com o brief | Partitura longa, BPM no prompt ou plano JSON válido |
| Canto | Escuta da emissão na mix; prosódia, timbre e fraseado por seção | ASR correto, tag “rasped vocal” ou direção em texto |
| Diversidade | Comparação de pares e do álbum, no plano e no áudio | Hashes diferentes, transposição ou troca de palavras |
| Integridade | Decode, duração, finitude, sinal ao longo do tempo, true peak nos arquivos efetivos | Duração do contêiner, RMS global ou token de fim isolados |
| Aprovação | Decisão do proprietário vinculada ao artefato e escopo ouvidos | Aprovação de 60 segundos extrapolada para cinco minutos/álbum |

## Antes de gerar

O agente do gênero dirige; Qwen 3.8 continua coordenando texto e plano. Letra/arranjo precisam de decisões concretas de motivo, groove, refrão, entrada/respiração vocal e encerramento. Não usar uma única forma e as mesmas células como fábrica de um álbum. `pemara-music-vocal-director` participa de músicas cantadas; `pemara-music-album-diversity`, dos lotes.

Escolha partitura ou geração direta conforme o controle necessário, sem declarar superioridade universal. Preserve o motor escolhido, idioma, letra fornecida e limites de duração. Parâmetros pertencem à tentativa e ao gênero; a direção aprovada de outro projeto não é preset universal.

## Depois de gerar

1. Identifique fonte nativa e exports por caminho/hash, duração efetiva, workflow e parâmetros reais.
2. Faça o QC técnico existente e examine o sinal ao longo da música. RMS global alto pode esconder um minuto final quase silencioso; cauda com hiss ou silêncio gerado não é desenvolvimento musical.
3. `pemara-music-listening-qc/scripts/screen_audio.py` faz triagem local de silêncio prolongado, descontinuidades e picos, sem alterar a fonte. Sinais suspeitos exigem revisão temporal; pausas intencionais não são reprovação automática.
4. Ouça a faixa inteira, com atenção a voz, entradas, transições, trechos densos e final. Compare com a intenção de gênero e com as faixas semelhantes do lote.
5. Separe o resultado técnico, a revisão de gênero/canto/diversidade e a decisão exata do proprietário. Sem áudio ouvido, use `LISTENING_PENDING`; não inventar evidência nem substituir escuta por embeddings, partitura ou métricas.

Se a ferramenta não reproduz ou não permite escuta real, declare essa limitação antes de afirmar qualidade. Uma publicação expressamente autorizada sem audição do proprietário mantém a pendência explícita; autorização de envio não torna a música artisticamente aprovada. Não converter a ausência de escuta numa alegação de revisão concluída.

## Correção com causa

- Falha de emissão, riff ou forma pede correção na composição/geração autorizada; ganho/EQ não corrigem sílabas quebradas, arranjo repetitivo ou clipping já impresso.
- Música curta pede desenvolvimento musical e vocal. Não completar minutos com silêncio, repetição de arquivo, stretch, corte disfarçado ou supressão isolada do token de fim. Continuar emitindo tokens pode gerar hiss e quase silêncio; medir duração não resolve isso.
- Não alterar o runtime para forçar duração como etapa rotineira da produção. Mudança de implementação exige tarefa própria, verificação técnica e escuta do resultado antes de multiplicar o método.
- Registre defeito ouvido/medido → hipótese → mudança concreta → resultado. Após duas falhas equivalentes, pare a repetição cega e reveja o método dentro do orçamento/escopo; não multiplicar seeds indefinidamente.
- Correção previamente autorizada prossegue sem pedir de novo o início. Pausa, cancelamento e proibição de gerar prevalecem. Ordem de apagar prevalece sobre a preservação rotineira; não reabrir o lote apagado.

## Registro mínimo por candidato

Registre `artifact_path`, `sha256`, `engine`, workflow/parâmetros, duração e limites pedidos, `technical_status`, `listening_status`, intervalos realmente ouvidos, achados/ações por gênero, vocal e diversidade, e decisão do proprietário com hash/escopo. Use `NOT_APPLICABLE` para voz de uma instrumental e diversidade de faixa avulsa.

`TECHNICAL_FAIL` e `REJECTED` impedem chamar o candidato de entrega qualificada. `LISTENING_REVIEWED` indica revisão realizada, não aprovação do dono. Nenhum desses campos autoriza gerar, publicar, treinar, instalar ou trocar de motor. Testes das skills comprovam configuração e comportamento dos auxiliares, não melhoria musical já ouvida.
