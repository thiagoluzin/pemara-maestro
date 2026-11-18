# Auditoria musical do Maestro — 08/10/2026

## Parecer

O Maestro tem uma base ampla para composição original, cover generativo e reinstrumentação por partitura. A instalação em disco está consistente nos verificadores consultados e 84 testes passaram. Isso ainda não comprova qualidade musical, fidelidade ao áudio de referência nem funcionamento de geração no estado atual do serviço.

Para o objetivo do proprietário — pegar a mesma música sertaneja e transformá-la em heavy metal — ACE-Step 1.5 XL em modo Cover é a opção generativa já integrada. Para preservar notas e canto com maior controle, a direção recomendada é separar o vocal original, revisar a transcrição, fixar a identidade musical e produzir outra instrumentação. Não há demonstração nesta auditoria de cópia fiel automática nota por nota.

Somente os arquivos desta pasta de auditoria foram criados. Nenhum motor, peso, skill, serviço, configuração de produção ou áudio existente foi alterado; nenhum job foi enviado.

## O que cada caminho faz hoje

| Caminho | Função real | Limite relevante |
|---|---|---|
| YuE2 — Criar música | Composição por direção, letra e ABC; opção de revisar partitura e duração automática | Não recebe o áudio original como referência de cover nessa rota. Não é a escolha para copiar a mesma canção. |
| ACE-Step 1.5 XL — Cover | Usa áudio original como condicionamento e gera uma releitura com outra direção de estilo | Preservação é aproximada. O controle de força não representa porcentagem de notas corretas. Pode mudar frases, timbres, letra ou vocal. |
| Partitura Primeiro — MuScriptor Large | Transcreve ou importa MIDI/MusicXML, oferece comparação A/B e trava a partitura revisada antes do arranjo | O contrato protege o MIDI aprovado; não prova que a transcrição inicial é igual à gravação nem que o áudio renderizado soa fiel. A rota atual é instrumental. |
| Maestro Produtor por stems | Demucs separa pistas; Basic Pitch e arranjador produzem a nova base, com avaliações de identidade e mix | Pode recolocar o stem vocal original; a separação pode conter vazamento/artefatos e a transcrição requer conferência. Não confundir com geração de outro cantor. |

No worker ACE, a opção de voz corresponde a permitir geração vocal; não há cópia e recombinação do stem vocal original como no caminho Demucs. Na interface, a voz preservada é corretamente desativada na rota Partitura Primeiro.

## Achados prioritários

### 1. A recomendação ACE pode atravessar uma reprovação técnica

`services/studio/music_ai_production.py:300` reduz a pontuação de candidatos tecnicamente reprovados, mas em `:351` define a recomendação apenas pela posição e pelo resultado de mix. Se todos falharem tecnicamente, um ainda pode ser recomendado. O worker em `services/studio/main.py:7341` usa a existência de recomendação como gate interno da rota ACE e pode então marcar o lote para revisão e visibilidade na biblioteca. Isso não é aprovação artística automática, mas enfraquece a separação entre candidato válido e candidato reprovado.

Reprodução offline: `gate_reproductions.json`, campo `failed_candidate_is_recommended: true`. Dois candidatos sintéticos reprovados tecnicamente, com métricas criativas favoráveis, bastaram para reproduzir a falha sem geração.

Correção recomendada: elegibilidade técnica deve ser obrigatória antes da recomendação e do gate interno; ausência de candidato elegível deve permanecer declarada, preservando os arquivos para diagnóstico.

### 2. Falta proteção consistente de pico na criação original e no cover

O grafo YuE2 em `services/studio/music_creation.py:94` decodifica e segue diretamente para `SaveAudioAdvanced` em `:122`. A finalização em `services/studio/main.py:3015` prepara o MP3 e os metadados, sem um gate equivalente de pico, loudness e conferência do arquivo de entrega.

O cover ACE ajusta ganho por pico de amostra. `services/studio/music_ai_audio.py:140` mede true peak, mas não o inclui em `technicalPass`. Um cenário sintético com pico de amostra de -1 dBFS, true peak de +0,4 dBTP e demais critérios válidos foi aceito. Reduzir o volume de um arquivo já saturado não reconstitui seus transientes.

Medições de arquivos reais existentes, com decode completo e SHA-256:

| Arquivo resumido | Duração | LUFS integrado | Pico de amostra | True peak | Amostras no teto segundo o contador |
|---|---:|---:|---:|---:|---:|
| YuE2 `63240317f2a2` FLAC | 332,28 s | -12,0 | 0,0 dBFS | +0,4 dBTP | 36 |
| YuE2 `1d113ca939d8` FLAC | 198,04 s | -12,6 | 0,0 dBFS | +0,7 dBTP | 61 |
| YuE2 `809933f7b866` FLAC | 297,16 s | -12,8 | -0,32 dBFS | aproximadamente 0 dBTP | 0 |
| Steel Legacy 01 — MP3 | 344,72 s | -18,3 | -4,74 dBFS | -4,7 dBTP | 0 |

Todos passaram no decode. Os valores mostram falta de margem nos três FLACs amostrados; não estabelecem, sem escuta, intensidade de distorção audível ou qualidade artística. O MP3 do álbum evidencia que uma finalização diferente pode preservar margem; não determina um volume ideal universal. Dados completos em `existing_audio_measurements.json`.

Correção recomendada: proteger margem antes da quantização/exportação, medir true peak também após a codificação final e escolher loudness conforme o material, preservando dinâmica. Não alterar os arquivos históricos automaticamente.

### 3. Fidelidade precisa ser verificada na referência, não apenas no MIDI derivado

A revisão A/B e o bloqueio da partitura são pontos fortes. O contrato MIDI impede alterações nas notas do score aprovado, mas um erro de transcrição fixado continua sendo erro em relação à música original. A documentação do MuScriptor declara erros possíveis em mixes densas/processadas e ausência de dinâmica/velocity transcrita. A interpretação expressiva do Maestro produz dinâmica para o novo arranjo; isso não equivale a recuperar integralmente a interpretação original.

Para cover, a avaliação deve conferir melodia principal, tom, acordes, andamento/mapa de tempo, entradas, duração de frases, refrão e ordem das seções. Similaridade por embeddings e duração próxima não provam igualdade desses elementos.

### 4. Preservar o cantor exige um caminho específico

Para manter a mesma letra, afinação, fraseado e gravação vocal, preservar o stem vocal original é mais controlável do que pedir que o cover generativo reproduza a voz. O caminho por stems já contém a recombinação vocal em `services/studio/music_reinstrument.py:1085`; Partitura Primeiro rejeita `keep_vocals` em `services/studio/music_score_first.py:573`.

A melhoria coerente é integrar vocal preservado à base por partitura revisada, com sincronismo e comparação A/B. É uma recomendação de implementação; esse fluxo combinado não foi implantado nesta auditoria.

### 5. Produção musical exige direção e escuta próprias

O Maestro já tem análise de forma/energia, planos por seção, interpretação expressiva, stems, crítica de mix e revisão humana. Ainda é necessário validar se uma base funciona como heavy metal: guitarras com articulação convincente, baixo ligado ao riff sem encobrir a voz, bateria com variação e viradas, refrão com desenvolvimento e dinâmica entre seções. As heurísticas de texto, métricas e um alvo fixo de volume não demonstram esses resultados sozinhos.

Para material sertanejo, convém conservar melodia vocal e progressão que tornam a canção reconhecível, enquanto se transforma acompanhamento, timbres e groove. O andamento não precisa ser acelerado para parecer metal; essa decisão deve ser explícita. Uma nova guitarra rítmica pode precisar de notas adicionais de acordes, sem alterar a melodia protegida: bloquear absolutamente todas as notas não substitui uma política musical de arranjo.

## Uso recomendado para sertanejo → heavy metal

**Experiência generativa:** usar áudio fonte no ACE-Step 1.5 XL/Cover, duração da referência e direção de metal. A documentação oficial sugere força entre 0,3 e 0,5 para mudanças grandes de gênero; isso concede mais liberdade e pode diminuir a fidelidade. Aumentar a força aproxima a estrutura original, mas também pode dificultar a mudança de estilo. Não anunciar força 80% como fidelidade musical 80%.

**Produção com prioridade de fidelidade:** separar o vocal; revisar/importar a partitura; fixar melodia, harmonia e mapa de tempo; arranjar guitarra, baixo e bateria; renderizar pistas; recolocar o vocal; conferir alinhamento, picos e mix; comparar com a referência e ouvir o candidato. Parte desse processo existe no Maestro, mas a integração completa descrita acima permanece recomendada.

## Evidência e limites

- Os quatro verificadores de instalação retornaram configurado: criação, cover ACE, reinstrumentação e score-first. Presença/configuração em disco não são testes de inferência.
- 84 testes dos módulos musicais passaram; saída preservada em `tests.log`. As duas falhas adicionais de gate foram reproduzidas separadamente por `check_recommendation.py`.
- O MCP `comfyui-local/server_info` não confirmou servidor disponível, registrou processo anterior e timeout de atualização. Não foi assumida fila vazia e não houve restart nem envio. Studio 8029 não apresentou listener na observação desta auditoria. Disponibilidade deve ser conferida novamente antes de geração autorizada.
- Nenhuma pasta de job foi encontrada no diretório configurado `dados/studio/music_reinstrument`. Isso não afirma que nunca existiram covers em outros locais. Não havia neste inventário um par original/cover para comparação musical.
- Os quatro arquivos foram medidos e decodificados, sem avaliação perceptual por escuta nesta sessão. Não há aprovação de voz, arranjo, fidelidade ou qualidade artística.
- A configuração ACE registra restrição comercial para os pesos do crítico MuQ-Eval. Isso diz respeito ao crítico instalado, não a uma conclusão genérica sobre todas as músicas ou todos os modelos.
- A skill TypeSafe foi aplicada como orientação de separar regras verificáveis de julgamentos semânticos. Não foi chamada API, enviado áudio ou introduzido custo.

## Fontes primárias consultadas em 08/10/2026

- [ACE-Step — guia para músicos](https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/ace_step_musicians_guide.md): cover, influência da referência e exemplo de mudança country → metal.
- [ACE-Step — parâmetros de inferência](https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/INFERENCE.md): `task_type=cover`, `src_audio` e `audio_cover_strength`.
- [MuScriptor Large — ficha oficial](https://huggingface.co/MuScriptor/muscriptor-large): representação, aplicações e limites de transcrição.
- [MuQ-Eval A1 — ficha oficial](https://huggingface.co/zhudi2825/MuQ-Eval-A1): contexto do crítico instalado.
- [TypeSafe — índice de documentação](https://docs.typesafe.ai/llms.txt): orientação obrigatória consultada.
