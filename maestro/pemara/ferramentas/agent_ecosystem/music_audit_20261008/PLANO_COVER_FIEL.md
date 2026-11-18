# Plano para transformar a mesma música em heavy metal com fidelidade verificável

Data: 08/10/2026. Estado: plano elaborado; implementação e geração não executadas.
Escopo: Maestro local, preservando YuE2, ACE-Step e a infraestrutura existente.

## Decisão recomendada

Criar uma rota de **arranjo fiel com voz preservada**, baseada na música original, em pistas separadas e numa partitura revisada. Usar ACE-Step para propostas opcionais de acompanhamento e experimentação. A versão final deve preservar os elementos definidos como identidade da canção e comprovar isso por arquivos, comparação musical e escuta.

Não foi encontrado nas fontes consultadas um método que comprove transformação automática de qualquer mix estéreo em outro gênero com 100% de fidelidade. Mudar timbres e acompanhamento produz outro áudio. É possível exigir igualdade exata em determinados ativos e eventos do projeto; isso precisa ser separado da qualidade perceptual e da exatidão da transcrição em relação à gravação.

## Resultado da pesquisa na comunidade

1. **O próprio debate do ACE-Step reconhece variação melódica.** Na discussão #209, ChuxiJ explica que o resultado fica entre cover e remix e frequentemente contém variações. Um participante relata mudanças de estilo em etapas. Esse relato é uma tentativa útil para experimentação, não prova de preservação total. Não alimentar automaticamente uma nova tentativa com a anterior: a comparação deve continuar usando a referência original. [Discussão original, comentários de 13/02 e 10/03/2026](https://github.com/ace-step/ACE-Step-1.5/discussions/209).

2. **Há falhas relatadas mesmo quando se busca uma melodia igual.** O issue #972 descreve uma canção semelhante com outra melodia. É um relato de usuário, sem benchmark controlado; reforça a necessidade de testar o resultado, em vez de confiar no nome do modo. [Issue original de 29/03/2026](https://github.com/ace-step/ACE-Step-1.5/issues/972).

3. **A comunidade de separação trabalha com modelos e combinações diferentes.** A discussão UVR #444 contém experiências com ensemble e modelos posteriores. Não existe ali comprovação de um vencedor universal. O repositório MSST oferece Demucs, BS-RoFormer, Mel-Band RoFormer e ensemble; UVR publica suporte RoFormer em beta. A proposta é comparar candidatos por faixa, mantendo Demucs como opção existente. [Discussão UVR](https://github.com/Anjok07/ultimatevocalremovergui/discussions/444), [implementação MSST](https://github.com/ZFTurbo/Music-Source-Separation-Training), [releases UVR](https://github.com/Anjok07/ultimatevocalremovergui/releases).

4. **Transcrever não elimina revisão.** MuScriptor Large produz eventos musicais, mas sua ficha documenta erros possíveis e ausência de velocity/dinâmica transcrita. Usá-lo como primeiro rascunho e corrigir a referência musical. [Ficha oficial](https://huggingface.co/MuScriptor/muscriptor-large).

5. **Há uma alternativa generativa para construir acompanhamento.** ACE-Step documenta `complete` e `lego` nos modelos base. Isso justifica um experimento de acompanhamento condicionado, sem assumir igualdade do vocal na saída nem compatibilidade já comprovada do worker local. O worker atual do Maestro utiliza `task_type="cover"`; esses outros modos precisam de integração e qualificação próprias. [Contrato oficial de inferência](https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/INFERENCE.md).

Consulta realizada em 08/10/2026. Relatos da comunidade foram separados de capacidades documentadas e de recomendações deste plano. Nenhum áudio remoto foi baixado ou usado para geração.

## Definir exatamente o que deve continuar igual

| Elemento | Política proposta | Como comprovar e onde há limite |
|---|---|---|
| Arquivo original | Imutável | SHA-256; decodificação completa; fonte preservada |
| Gravação vocal | Reutilizar a pista fornecida ou a extração revisada | Hash e comparação PCM do ativo preservado; extração de mix não é necessariamente igual ao stem verdadeiro |
| Letra e idioma | Manter canto original | Reutilização vocal; conferência do texto e das frases; ASR é apoio e pode errar em canto |
| Melodia principal e hooks | Não adicionar, remover ou trocar notas protegidas | Eventos da partitura revisada, referência auditiva e inspeção do áudio de cada instrumento |
| Harmonia | Preservar progressão e modulações | Mapa de acordes revisado por seção; novas inversões/voicings definidos no arranjo |
| Tempo e forma | Preservar mapa de tempo, entradas e ordem das seções | Timeline em amostras/tempo musical, marcadores e alinhamento; não substituir rubato por BPM fixo |
| Acompanhamento | Transformar em metal | Guitarra, baixo e bateria novos, subordinados à harmonia e ao canto; novas notas rítmicas são permitidas nessa camada |
| Mix e master | Produzir outro equilíbrio sonoro | Medidas do arquivo final e escuta; o master novo não tem o mesmo PCM da gravação original |

Se a pessoa fornecer o stem vocal verdadeiro, pode-se preservar esse ativo exatamente no projeto. Se fornecer apenas MP3/mix estéreo, o vocal separado é uma estimativa: não anunciar recuperação perfeita. Mesmo stem imutável pode soar diferente dentro de outra mix. EQ, compressão, ganho, reverb e resampling devem ter registro próprio, preservando o ativo anterior.

## Sequência de produção

### Etapa 1 — Fonte e referência musical

- Receber o arquivo disponível, priorizando sessão multipista ou stems originais quando existirem. Manter também a gravação estéreo para comparação.
- Registrar hash, codec, duração, canais e taxa. Criar cópia de trabalho em formato adequado, registrando qualquer conversão; não afirmar que converter MP3 para WAV recupera detalhes perdidos.
- Criar mapa de seções, compasso, tempo variável, acordes, tonalidade/modulações, melodia principal e respostas instrumentais reconhecíveis.
- Para sertanejo em dupla, identificar voz principal, segunda voz e respostas. Conferir as duas vozes; uma melodia monofônica não descreve toda a identidade.

**Entrega:** original preservado, mapa musical e referências por seção. Erros ou lacunas ficam explícitos.

### Etapa 2 — Voz preservada e separação comparada

- Usar stems fornecidos diretamente. Quando só houver mix, iniciar pelo Demucs já instalado.
- Em fase de qualificação, comparar um checkpoint especializado BS-RoFormer e um Mel-Band RoFormer em ambiente separado. Fixar pesos/configuração/revisão e conferir sua licença antes de adoção. Não instalar UVR inteiro como requisito do backend se uma integração local isolada atender.
- Avaliar refrão, segunda voz, sibilantes, reverb e transientes. Procurar vazamento de viola/sanfona e perdas de sílabas. Ensemble só entra se realmente melhorar esse material; não combinar por padrão.
- Revisar extração e fixar o stem escolhido. Nenhum denoise, mudança de pitch ou time-stretch automático deve alterar a voz depois dessa revisão.

**Entrega:** vocal revisado, demais stems, comparação e recibo da separação. Sem referência vocal verdadeira, relatar qualidade observada, sem porcentagem de recuperação.

### Etapa 3 — Partitura corrigida e identidade fixada

- Usar MuScriptor Large como rascunho e permitir importar MIDI/MusicXML corrigidos. Aproveitar o fluxo A/B existente.
- Conferir notas contra a gravação, especialmente melodia, baixo/harmonia, modulações e hooks. Revisar manualmente pontos ambíguos; manter conflitos até resolução.
- Fixar a camada de identidade separadamente da camada de acompanhamento. Guardar eventos canônicos e seu hash.
- Definir interpretação da base nova por pista, preservando a geometria dos eventos protegidos. Velocity e articulação criadas para guitarra/bateria não devem ser confundidas com dinâmica recuperada da fonte.

**Entrega:** partitura de identidade revisada, mapa de acordes/tempo e contrato de alterações permitidas. Igualdade a esse MIDI é verificável; fidelidade dele à gravação exige a revisão anterior.

### Etapa 4 — Arranjo de metal por pistas

- Manter andamento e canto na primeira versão. Não acelerar nem transformar a voz em grito para caracterizar metal sem direção específica.
- Produzir riffs a partir da harmonia: guitarra rítmica com palm mute/power chords quando adequados, aberturas de refrão e respostas que preservem os hooks. Respeitar a região da voz e evitar dobrar toda a melodia continuamente.
- Baixo acompanha o arranjo e preserva os movimentos harmônicos importantes. Bateria desenvolve verso/refrão, com viradas e variação, sem pulso idêntico na faixa inteira.
- Priorizar guitarras com articulações reais: instrumento amostrado adequado ou takes gravados/DI e processamento de amplificador. Duplicar o mesmo áudio para esquerda/direita não equivale a duas performances.
- O score-first atual encaminha guitarra para FluidSynth/MS Basic em `music_score_first.py:1189`; manter essa rota histórica, mas qualificar outro renderer para a proposta de metal. Falta de instrumento qualificado deve ficar visível, sem substituição silenciosa.
- ACE-Step pode sugerir base instrumental ou frases. Qualquer proposta precisa ser alinhada e comparada; se alterar a identidade, reconstruir/corrigir a pista correspondente. A geração não altera a referência fixada.

**Entrega:** guitarra, baixo, bateria e opcionais separados, MIDI quando aplicável e plano do arranjo. A qualidade do timbre precisa de escuta.

### Etapa 5 — Integração vocal, mix e conferência

- Integrar a opção de vocal preservado ao score-first. Conservar referência de tempo e offsets em amostras; compensar latência dos renderers/processadores.
- Manter no projeto o vocal fixado, com processamento de mix versionado. Não regenerar letra ou cantor no modo fiel.
- Renderizar WAV de trabalho, master sem perdas e MP3 de entrega. Checar o arquivo codificado, não apenas o WAV intermediário.
- Bloquear clipping, decode inválido, duração indevida e true peak acima do teto contratado. Proposta inicial: teto de -1 dBTP para o arquivo final, sujeito à qualificação dos encoders. LUFS deve refletir dinâmica/estilo e ser registrado, sem meta universal de volume.
- Comparar A/B com volume de escuta ajustado para evitar preferência automática pela versão mais alta. Apresentar voz solo, base solo e mix completa.

**Entrega:** candidato técnico válido, pistas separadas, medições e A/B. Aprovação artística continua própria.

### Etapa 6 — Piloto e qualificação do processo

Primeiro piloto: uma música escolhida, com trecho de verso e refrão para corrigir separação, identidade e timbre antes de renderizar tudo. Depois validar a faixa completa, incluindo pontes, viradas, segunda voz e caudas.

Conjunto inicial de qualificação proposto: três faixas representativas — voz/violão simples, dupla sertaneja com produção densa e uma gravação com variações de tempo. Pelo menos um caso com stems verdadeiros é necessário para medir separação contra referência. Usar material disponível/autorizado para o projeto; não baixar exemplos arbitrários.

Testes negativos devem incluir: nota protegida removida, acorde trocado, verso deslocado, voz cortada, falta de evidência de instrumento, todos os candidatos reprovados e overshoot após MP3. Cada um precisa produzir bloqueio correto, sem perder mídia ou histórico. Os limiares de alinhamento e pitch serão calibrados com essas referências; não inventar uma porcentagem global de fidelidade.

## Plano de engenharia no Maestro

| Ordem | Trabalho concreto | Componentes previstos | Critério de conclusão |
|---|---|---|---|
| P0 | Corrigir recomendação e gates de pico | `music_ai_production.py`, `music_ai_audio.py`, finalização em `main.py`/`music_creation.py` | Candidato tecnicamente falho nunca recomendado; true peak do arquivo final participa do gate |
| P1 | Contrato musical e evidências por seção | Novo serviço de contrato, integração com `music_score_first.py` e armazenamento de jobs | Fonte, vocal, identidade, acompanhamento e aprovações têm hashes/versões separados |
| P2 | Vocal preservado no score-first | `music_score_first.py`, `music_performance_mix.py`, `main.py`, `music-reinstrument.js` | Vocal escolhido mantém seu ativo e tempo; processamento/delay explicitamente registrados |
| P3 | Separação especializada opcional | Adaptador isolado junto ao runtime de áudio | Comparação real com Demucs e registro de configuração/checkpoint; adoção por evidência |
| P4 | Renderer de guitarra e direção do arranjo | Adaptador de instrumento, `music_orchestrator.py`, planos por seção | Articulação, notas protegidas e harmonia verificadas; pistas exportáveis e audíveis |
| P5 | Revisão A/B e validação final | Interface, serviços de identidade, QC e entrega | Revisor localiza divergências e aprova dimensão por dimensão; entrega tem recibo verificável |

Os nomes de novos serviços/contratos são propostas, não módulos já implementados. Preservar jobs existentes e introduzir versão nova optativa antes de qualificar o padrão. Rota antiga permanece identificada; nunca chamar um cover generativo de cópia musical comprovada apenas por pontuação do crítico.

Estados previstos: `SOURCE_READY` → `STEMS_REVIEW_PENDING` → `IDENTITY_REVIEW_PENDING` → `IDENTITY_LOCKED` → `ARRANGEMENT_READY` → `TECHNICAL_QC_PASSED` → `PENDING_HUMAN_REVIEW` → `OWNER_APPROVED`. Falha mantém etapa e evidências; correção produz outro candidato. Nenhum ranking atravessa um gate reprovado.

## Verificações independentes

| Dimensão | Verificação proposta | Declaração permitida |
|---|---|---|
| Integridade | Hash, cabeçalhos e decode | Arquivo íntegro |
| Vocal preservado | Identidade do ativo PCM e registros de processamento | Ativo vocal mantido; origem fornecida ou extraída declarada |
| Eventos protegidos | Comparação exata com score revisado | Nenhuma alteração nos eventos protegidos do projeto |
| Harmonia e forma | Mapa revisado, marcadores e análise por seção | Estrutura conferida com a referência |
| Áudio musical | Conferência em stems de pitch, ataques, caudas e alinhamento | Medidas dentro das tolerâncias qualificadas; pontos não mensuráveis declarados |
| Produção | Escuta de articulação, mix, desenvolvimento e artefatos | Parecer de produção, com trechos e motivos |
| Decisão final | Avaliação do proprietário | Candidato aprovado para esse resultado |

Uma medida de similaridade não substitui nenhuma dessas verificações. A análise de áudio não deve usar alinhamento elástico para esconder uma mudança de tempo que o contrato proíbe.

## Direção e skills a especificar na implementação

Responsabilidades previstas: produtor musical define o arranjo por seção; supervisor de identidade confere referência e partitura; engenheiro de áudio responde por pistas, sincronismo e exportação; revisor artístico registra escuta. São funções, não exigência de executar subagentes.

As futuras skills precisam exigir referência original persistente, separar elementos protegidos/permissíveis, impedir aprovação por checklist e orientar correções pelo trecho afetado. Uma rejeição de guitarra não deve causar regeneração da voz ou dos aspectos aprovados.

TypeSafe foi consultada por exigência do projeto. A separação de dimensões e critérios combina com o padrão de pontuação composta, mas integridade e igualdade musical ficam em código; um julgamento semântico não substitui provas nem aprovação. Este plano não exige API TypeSafe nem envio de áudio. [Índice vivo](https://docs.typesafe.ai/llms.txt), [pontuação composta](https://docs.typesafe.ai/patterns/composite-scoring). A página específica do guia de construção não abriu nesta consulta; o índice e o padrão pertinente estavam acessíveis.

## Limites de execução desta entrega

Plano e pesquisa concluídos. Sem instalação, download de pesos, compra de instrumentos, restart, alteração de produção ou geração. Antes de testes que usem ComfyUI, confirmar serviço/runtime e fila pelo MCP autorizado; os registros de disponibilidade da auditoria anterior não são uma prova de estado atual. O backend do Maestro mantém sua autonomia prevista nas instruções do projeto.

Resultado esperado da implementação: a mesma composição reconhecível, com voz e identidade controladas e acompanhamento de metal convincente, sustentada por evidências e escuta. O termo “100%” deve acompanhar apenas a dimensão cuja igualdade foi realmente verificada.
