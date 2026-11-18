# Música local: do prompt à canção pronta no Maestro

Pesquisa consultada em 05/10/2026. Escopo: modelos locais, programas da comunidade com código reaproveitável e desenho de um fluxo que dispense escrever letra ou interpretar partitura. Fontes dos autores, documentação e código local foram examinados; não foi feito benchmark comparativo de áudio nesta pesquisa.

## Conclusão para o proprietário

Priorizar a automação do YuE2, cujo resultado o proprietário gostou, mantendo a escolha explícita dos motores. A interface principal deve aceitar uma descrição e gerar a música completa: a IA escreve a letra quando houver vocal; a composição ABC do YuE2 acontece internamente e segue para síntese sem um segundo comando. A escuta do proprietário ocorre depois que existe áudio. Partitura, letra editável e parâmetros técnicos podem continuar disponíveis em ajustes opcionais.

## O que explica a experiência atual

Verificado diretamente no workspace:

- `app/index.html`, linha 410: a caixa `gen-music-instrumental` começa marcada. O modo padrão envia uma solicitação instrumental.
- O formulário apresenta as etapas YuE2 separadas e exige a caixa de revisão da partitura.
- `services/studio/music_creation.py`: a validação exige letra para vocal e `music_abc_reviewed` para áudio YuE2. O builder cria dois grafos separados, um para ABC e outro para áudio.
- `ferramentas/audio_neural/music_ai_runtime/ace_create_cli.py`: usa a descrição e letra fornecidas, chama `generate_music(handler, None, ...)` e desliga o planejamento por LM. Assim, não aciona o escritor automático do ACE-Step.
- No próprio source ACE-Step instalado, `acestep/inference.py` contém `create_sample`: recebe a ideia e devolve descrição, letra e metadados. Há pastas locais para os planners 1.7B e 4B; isso é inventário em disco, não validação de sua carga nesta pesquisa.
- Consulta somente de inventário ao Ollama local em `127.0.0.1:11435/api/tags`: `qwen3.5:4b` está disponível, além de modelos maiores. Sua qualidade como letrista em português ainda precisa de teste.

Os módulos atuais `music_orchestrator.py` e `music_producer.py` tratam orquestração/reinstrumentação; a leitura não identificou neles um escritor de letras conectado à criação de canções.

## Modelos relevantes

| Modelo | Capacidade documentada | Uso recomendado no Maestro |
|---|---|---|
| **YuE2-3B** | O pipeline oficial escreve um plano de melodia/acordes e o realiza como canção com vocal e acompanhamento; também permite geração direta. | Primeira prioridade de automação, preservando o motor escolhido. |
| **ACE-Step 1.5** | O modo Simple cria descrição, letra e metadados por LM; a síntese usa esses dados. O app oficial ainda apresenta criação do conteúdo e geração como ações separadas. | Encadear as funções no backend do Maestro em um único trabalho. |
| **LeVo 2 / SongGeneration 2** | Geração de canções com voz e acompanhamento, condicionada por letra e direção musical. | Preservar a integração existente e ligar a mesma preparação automática de letra. |
| **HeartMuLa** | Família com gerador condicionado por letra/tags, codec e transcritor; o repositório recomenda uma versão pública 3B. A versão 7B citada como interna não deve ser tratada como download disponível. | Candidato adicional para comparação futura; não exige trocar o motor atual. |
| **DiffRhythm / DiffRhythm 2** | Canções completas com voz; o exemplo de inferência do 2 usa letra e áudio de referência. | Candidato secundário; ter vocal não significa resolver sozinho o fluxo de apenas prompt. |
| **MusicGen** | O model card documenta a remoção de vocais dos dados de treinamento. | Não priorizar para resolver letra cantada. |
| **SongBloom** | O trabalho dos autores descreve geração coerente de canções. | Manter no levantamento; o endereço original do repositório não abriu nesta consulta, portanto não recomendar instalar um fork como se fosse uma atualização oficial. |

Fontes: [YuE2 oficial](https://github.com/multimodal-art-projection/YuE), [ACE-Step: modo Simple](https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/GRADIO_GUIDE.md), [model card Tencent SongGeneration](https://huggingface.co/tencent/SongGeneration/blob/main/README.md), [HeartMuLa oficial](https://github.com/HeartMuLa/heartlib), [DiffRhythm](https://github.com/ASLP-lab/DiffRhythm), [DiffRhythm 2](https://github.com/ASLP-lab/DiffRhythm2), [MusicGen model card](https://huggingface.co/facebook/musicgen-large), [SongBloom: artigo dos autores](https://arxiv.org/abs/2506.07634).

O conteúdo Tencent apareceu no resultado indexado, mas a abertura direta falhou, assim como o antigo GitHub `tencent-ailab/songgeneration`. Um repositório que se apresenta como oficial, `AMAImedia/SongGeneration2-LeVo2`, foi lido, mas a autoria/continuidade em relação ao endereço original não foi estabelecida. Não basear uma troca de source local somente nessa descrição.

## Programas e sistemas reaproveitáveis

| Projeto | O que foi confirmado | Aproveitamento sugerido |
|---|---|---|
| [**YuE2 Studio — vrgamegirl19**](https://github.com/vrgamegirl19/Yue2_Studio) | Código Apache-2.0; sala de escrita com LLM e lotes que escrevem e renderizam sequencialmente; interface web. | Melhor referência próxima do YuE2 atual para letra, progresso e continuação automática. |
| [**YuE2-Radio**](https://github.com/PasiKoodaa/YuE2-Radio) | Código MIT; escreve letras via LM Studio e gera canções com YuE2/audio.cpp; inclui português e validação de formato. | Reaproveitar o encadeamento e as validações para uma canção solicitada, sem criar rádio contínua por padrão. |
| [**Remiqora**](https://github.com/inikolax/remiqora) | Código MIT; reúne ACE-Step e YuE2; backend FastAPI; modo simples ACE-Step; biblioteca, editor e exportação. O próprio autor o declara em desenvolvimento. | Boa referência de integração entre motores, biblioteca e gestão de memória; adaptar componentes ao Maestro existente. |
| [**ACE-Step Studio — timoncool**](https://github.com/timoncool/ACE-Step-Studio) | Descreve canção a partir de uma ideia, assistente local de escrita e planner ACE-Step; várias formas de exportação. | Examinar contratos de preparação do prompt, letra e entrega. Usa também runtime C++, distinto do worker Python atual. |
| [**YuE2 Studio — timoncool**](https://github.com/timoncool/YuE2-Studio) | App Windows com assistente de escrita local, geração vocal e código MIT. | Referência de experiência de uso; não presumir equivalência entre seu yue2.cpp e o ComfyUI atual. |
| [**YuE2 Studio — krakenunbound**](https://github.com/krakenunbound/yue2-studio/blob/main/USER_GUIDE.md) | Guia documenta letras e título automáticos no modo Live, usando opção Local LLM compatível com Ollama. | Padrão de escritor local e criação sem intervenções técnicas. Verificar a licença do código antes de copiar componentes. |
| [**AudioSlopServer**](https://github.com/stevelittlefish/AudioSlopServer) | Servidor que compartilha uma GPU entre serviços e entrega trabalhos/artefatos por API; implantação descrita com Docker. | Referência secundária de coordenação; não resolve sozinho a experiência de prompt e letra. |

[DoREMii](https://github.com/jaytonmack111-commits/DoREMii) mostra ACE-Step com escritor Ollama/Qwen, mas seu README declara que o repositório público não está licenciado como open source. Pode servir de referência conceitual; não foi selecionado como fonte de código reutilizável.

As licenças dos aplicativos são distintas das dos pesos. Para YuE2, conferir o [LICENSE publicado pelos autores](https://huggingface.co/m-a-p/YuE2-3B/blob/main/LICENSE), em vez de adotar interpretações divergentes dos READMEs de terceiros. Não é necessário transformar essa verificação em um campo técnico do formulário do usuário.

## Proposta concreta de fluxo

**Descrição → direção e letra por IA local → composição interna quando necessária → síntese → player e MP3.**

1. Campo principal: “Descreva sua música”. Um botão: “Gerar música”. Motor continua selecionável.
2. Voz automática como padrão; “Instrumental” fica disponível quando o usuário quiser sem voz. Idioma e duração podem ser entendidos pelo prompt ou escolhidos opcionalmente. Quando não especificados, o produto precisa de padrões visíveis e simples.
3. Escritor local produz título, direção, idioma e letra estruturada. Primeiro candidato de baixo custo operacional: Qwen já instalado no Ollama, com teste de escrita PT-BR. Para ACE-Step, comparar com `create_sample` nativo antes de escolher a preparação definitiva.
4. YuE2 gera ABC e segue automaticamente para áudio no mesmo trabalho. Fazer validações técnicas de estrutura; não declarar falsamente que o proprietário revisou a partitura. Criar uma ação automática própria em vez de forçar `music_abc_reviewed=true`.
5. Preservar prompt, letra e ABC para repetir ou editar; mostrá-los apenas quando solicitado. O usuário avalia a música ouvindo o resultado.
6. Progresso: “Criando letra”, “Compondo”, “Gerando áudio”, “Preparando MP3”. Falhas mostram a etapa e permitem tentar novamente sem apagar a fonte anterior.
7. Planejamento de texto e síntese devem respeitar o coordenador de GPU existente. Modelos grandes de texto e música não precisam permanecer carregados juntos. Não adotar os scripts de gerenciamento/restart dos programas comunitários sobre os serviços atuais.

Para um grafo YuE2 automático no ComfyUI, conectar a saída real de `YuE2GenerateABC` ao campo ABC de `YuE2GenerateMusic` e validar o grafo exato por MCP antes de geração autorizada. A combinação precisa manter o contrato dos nós instalados; não trocar automaticamente pelo runtime de um aplicativo comunitário.

## Ordem recomendada e critérios de aceite

Primeiro: automatizar letra e sequência YuE2 no Maestro. Segundo: expor o mesmo modo simples no ACE-Step, aproveitando sua função nativa. Terceiro: comparação auditável com LeVo 2 e candidatos novos, somente quando houver direção para instalação/testes.

Aceite do produto: prompt sem letra deve chegar a áudio vocal; pedido instrumental deve ficar sem vocal; nenhum conhecimento de ABC/BPM é obrigatório; erro do escritor não vira instrumental silenciosamente; cancelamento funciona em cada etapa; repetição mantém o pedido; resultado toca e baixa MP3; escolha do motor é respeitada. A qualidade da composição, do vocal em português e da letra requer escuta do proprietário, separada dos testes de infraestrutura.

## Limites desta entrega

Pesquisa e proposta concluídas. Não foi instalada nova aplicação, iniciado treino, alterado o fluxo em produção ou gerada música nesta etapa. Capacidades dos novos projetos foram verificadas em documentação; não comprovadas em execução neste computador.

A skill TypeSafe obrigatória foi lida e o índice vivo consultado. Páginas específicas de conceitos não abriram pela ferramenta web nesta consulta. A proposta mantém código no controle da sequência; escrita criativa fica com um gerador de texto local. Nenhuma credencial TypeSafe foi acessada e nenhuma API paga foi adicionada.
