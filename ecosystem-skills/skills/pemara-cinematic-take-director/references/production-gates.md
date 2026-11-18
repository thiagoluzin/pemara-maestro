# Gates de produção e publicação

Texto operacional extraído da skill para leitura por etapa; não é histórico opcional. O AGENTS e o contrato específico vigente prevalecem.

## Intenção de publicação na internet

Quando o pedido atual afirmar que o vídeo será feito para publicação na internet, ativar o
perfil `social_v1` **antes do roteiro e das âncoras**. “Esse vídeo será feito para publicação na
internet”, “quero postar este vídeo no Threads” e “faça um vídeo para Shorts” são exemplos.
Não ativar por prints, citações, exemplos hipotéticos ou instruções negadas. Não alterar projetos
antigos em lote. As instruções explícitas de silêncio, contemplação, duração, formato e estilo
continuam valendo; não impor explosões, volume alto, cortes constantes ou 9:16.

No Maestro, criar o projeto com `distributionMode: auto` e o pedido no `objective`; a API detecta
a intenção. Para um projeto existente, usar o helper canônico (leitura por padrão):

```powershell
python E:/Pemara/maestro/pemara/ferramentas/video_global_engine/tools/prepare_internet_publication.py --project <id-exato> --brief-file <pedido-atual.txt>
```

Quando a criação/alteração desse projeto já estiver autorizada, adicionar `--apply` para persistir
o pedido via Studio. Nunca usar o gatilho como autorização de GPU ou publicação. O helper não
altera o objetivo original, não renderiza e não acessa contas sociais.

O diretor deve escrever e salvar os campos `audience`, `promise`, `emotion`, `opening`,
`alternativeOpening`, `progression`, `payoff`, `mobileFraming`, `silentComprehension` e `constraints`
em `--plan-file <direcao.json> --apply`, ou na seção **Publicação na internet** do Maestro.
Recomendar uma das duas aberturas por escrito; não gerar duas versões automaticamente.
Preencher com escolhas específicas da cena, não slogans ou os nomes dos campos. A API bloqueia
geração sem contrato preenchido e exige revisão após mudar briefing/formato. Completude não
equivale a aprovação artística; as aprovações e gates deste workflow permanecem independentes.

Relacionar causa, reação e consequência em cada beat; apresentar contexto compreensível e cumprir
a promessa no desfecho. Conferir o MP4 real, inclusive legibilidade no celular e sem som. Preparar
um pacote somente a partir do master exato aprovado, preservando seus bytes. Título, capa e
legendas continuam pendentes de revisão. Não publicar nem autorizar publicação automaticamente.
Resultados de alcance são métricas agregadas informadas pelo proprietário, vinculadas ao pacote
e à plataforma; deixar ausências explícitas. Não inventar pesos, limiares, causalidade ou previsão
de views. Comparações são descritivas e exigem janelas/durações comparáveis.

## Padrão canônico live action do Maestro

Para qualquer sequência live action do Maestro, e obrigatoriamente quando o proprietário pedir os
"mesmos moldes do Vejito", ler `references/vejito-liveaction-standard.md` antes de escrever o
manifesto ou gerar âncoras. O projeto
`vejito_super_boo_3x10_continuo_liveaction_foley_v1` é o padrão canônico declarado pelo
proprietário. Auditar seus artefatos reais; não reconstruir o método de memória.

Herdar a estrutura, não os personagens ou assets: takes principais completos, fronteiras
compartilhadas em movimento, microtrechos internos, aprovação humana take a take e montagem somente
de bitstreams aprovados. Manter no Maestro apenas os takes principais; âncoras e microtrechos são
evidências internas do take.

Antes da GPU, executar:

```powershell
python scripts/sequence_regression_gate.py <production_manifest.json> --stage contract
python scripts/sequence_regression_gate.py <production_manifest.json> --stage anchors
```

Antes da montagem, executar `--stage assembly`. Falha no gate bloqueia a próxima etapa.

O motor escolhido pelo proprietário também é parte do contrato. Se ele pediu MiniMax, não trocar
por LTX, Wan ou outro provedor para "facilitar" uma etapa sem uma nova autorização explícita.
Registrar o engine e o perfil em cada take e reprovar uma sequência que mistura engines sem decisão
humana documentada.

## Gate de direção de arte live action

"Live action" é um contrato de material e fotografia, não uma palavra decorativa no prompt. Criar
uma única bíblia visual da sequência com materiais físicos por personagem, anatomia, ambiente,
dano persistente, lente, luz, paleta e modos de render proibidos. Comparar folhas de contato de
âncoras e dos MP4s reais com a referência aprovada.

Reprovar o take inteiro se qualquer personagem virar anime, cel shading, ilustração, render de jogo,
CGI plástico/limpo ou cosplay; se pele, tecido, metal ou bioarmadura perderem microtextura física;
ou se anatomia, figurino, luz e cenário quebrarem a rota visual. Não recortar a parte "boa" de um
take visualmente contaminado para misturá-la com outra rota.

Os passes são independentes e ordenados:

1. `ART_DIRECTION_PASS`;
2. `CINEMATIC_PASS`;
3. `MOTION_PASS`;
4. `TECHNICAL_PASS`;
5. `HUMAN_APPROVED` para o artefato exato.

Passe técnico nunca compensa falha artística ou cinematográfica.

## Gate de identidade, anatomia e âncoras

Antes de qualquer imagem ou vídeo, criar uma matriz de identidade por personagem com: quantidade,
escala relativa, cores, materiais, anatomia obrigatória, elementos proibidos e estado por beat. Uma
descrição genérica como "preservar o personagem" não basta. Para criaturas, robôs e múltiplos
personagens parecidos, explicitar também apêndices, asas, cauda, membros, silhueta e quem pode ou não
aparecer em cada intervalo.

Âncora aprovada é um asset imutável: caminho, SHA-256, metadata e escopo de aprovação. Quando o
proprietário disser para usar as fotos aprovadas, não gerar substitutas, não mudar enquadramento e
não reinterpretar geometria. Se a própria âncora estiver errada, rejeitá-la e aprovar uma correção
antes do vídeo; nunca esperar que o modelo invente durante o take um elemento ausente no quadro
inicial.

Marcar `identity_risk: high` ou `critical` quando houver elenco parecido, anatomia frágil, contagem
exata, mudança de forma ou ação longa. Planejar controles e evidência reforçados conforme a rota.
Âncoras intermediárias aprovadas são úteis em transformação/pose técnica quando qualificadas;
combate contínuo start-only não pode recebê-las por regra genérica. A ficha original, o bloco fixo
de identidade e o QC temporal continuam obrigatórios; uma âncora isolada não prova fidelidade.

O QC deve inspecionar o MP4 real, não apenas prompt, metadata ou imagens de entrada. Conferir no
mínimo início, 25%, 50%, 75%, fim e todos os beats de contato/transformação; depois assistir ao
arquivo completo. Qualquer alteração de contagem, escala, cor, anatomia, estilo ou identidade
reprova o take inteiro.

### Foto aprovada pelo proprietário — 2026-09-26

Direção expressa: remover a análise NVIDIA NIM do workflow e do Maestro.
A foto aprovada pelo proprietário é a referência visual. Não solicitar chave externa,
consentimento de análise ou recibo NVIDIA para liberar I2V. Preservar a imagem original,
hash, escopo de aprovação, identidade e direção de movimento. Validar o grafo e a
admissão GPU pelo MCP; conferir o vídeo gerado e obter sua avaliação artística.
Aprovar foto não aprova automaticamente o vídeo ou a montagem.

## Gate universal de transicoes

Toda fronteira deve usar corte cinetico direto entre fontes aprovadas e compativeis, permanecer
dentro de take ininterrupto ou usar conector causal somente quando a rota permitir e o escopo
autorizar. `generatedConnectorAllowed: false` bloqueia emendas geradas. Crossfade/xfade, freeze,
hold, cauda estatica, reset e oclusao para esconder troca de movimento sao proibidos. Um conector
permitido herda vetores de corpo, objetos, efeitos e camera, progride e entrega movimento util.

O contrato tambem vale dentro de todo take gerado, mesmo quando ele nao e um conector.

A acao deve ocupar a duracao inteira. Exigir beats temporais explicitos e movimento util de
sujeito, ambiente e camera em `0-30%`, `30-70%` e `70-100%`. Evento concluido cedo seguido de pose
sustentada reprova, mesmo sem quadros literalmente identicos.

Em conectores first/last-frame, as duas ancoras devem vir de trechos com movimento visivel antes e
depois do quadro escolhido. Nao usar a pose final parada de um take nem o primeiro quadro parado do
seguinte.

Para toda transicao I2V/T2V, exigir quatro pilares antes de liberar GPU e confirmar os mesmos
quatro pilares por inspeção visual antes de aprovar ou montar:

1. `evident_camera`: deslocamento fisico legivel de camera com mudanca real de perspectiva;
   zoom, rack focus, pan/tilt, tremor ou deriva isolados nao bastam.
2. `real_depth`: primeiro plano, plano medio e fundo com deslocamento diferencial, oclusao ou
   mudanca coerente de escala; parallax 2D isolado nao basta.
3. `internal_action`: evento fisico legivel e pelo menos dois elementos movendo-se
   independentemente da camera; luz, fumaca e particulas so apoiam o evento.
4. `clear_progression`: inicio, meio e fim materialmente diferentes, estado final alterado e saida
   que motive corte seco, impacto musical ou conexao direcional.

Ausencia de qualquer pilar reprova o take. Reset, reversao gratuita, cauda estatica e "living
photo" tambem reprovam. Aplicar esta regra a todo projeto e modelo, inclusive quando a imagem-ancora
ja estiver aprovada.
