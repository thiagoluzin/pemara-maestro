# Face Refine removido por ordem do proprietario

Em 03/10/2026 o proprietario rejeitou Face Refine e solicitou o video original. Foram verificados 291 arquivos e alterados 58 workflows; o passe, etapa do Maestro e exportacao do no foram removidos. ComfyUI e Studio recarregados; 148 testes passaram. O original foi restaurado no Maestro e aprovado pelo proprietario. A protecao Sage para sequencias longas permanece ativa. Recibo: `receipts/owner_removal.json`. Conteudo abaixo e historico da tentativa rejeitada.

# H3 Face Refine local — 03/10/2026

Solicitação do proprietário: ativar Face Refine em todos os seus workflows H3.

O nó `PemaraH3FaceRefine` detecta rostos com YuNet CPU (anime ONNX como alternativa
quando não há detecção humana), recorta, executa um passe H3 Base FL2VA +
SageAttention, 12 passos, denoise 0,45, canvas 512, e recompõe a máscara.
O áudio de origem segue diretamente para o vídeo final. O MP4 original é salvo
antes da análise. Sem rosto detectado, os frames originais seguem intactos.
Falha do detector é erro; não vira ausência de rosto.

Fontes T8 GPL-3.0-or-later fixadas em
`772ce05a4531fe5452e277a649ff4dab9fc03418`. Somente três módulos são integrados;
hashes e licença ficam no plugin. Não se instala o pacote T8 inteiro.

## Cobertura

`receipts/deployment.json` registra backups e hashes das alterações. O inventário
contém 34 workflows: 17 grafos API, 11 editáveis, seis descritores. O handler do
ComfyUI também inclui o passe em novas submissões H3 provenientes de grafos antigos.
Os arquivos históricos de projetos, renders existentes e filas não são migrados.
O Maestro incorpora o passe no grafo antes de registrar a submissão.

Cobertura da etapa Face Refine não significa que todos os templates experimentais
sejam executáveis: alguns já tinham classes ausentes ou referências parciais.
O preflight MCP registra essas lacunas separadamente. Não se trocam motores ou
instalam dependências opcionais para esconder uma reprovação.

## Evidência

161 testes de contratos/backend e cinco testes CPU passaram. O diagnóstico MCP
`710430db-92a8-4bbe-b4d7-661a6a5dffe8` executou o H3 e recompôs cinco frames
de um rosto, com `mask_outside_bit_exact: true`, nenhum fallback e Sage conectado.
Esse teste isolado não mede consistência temporal em 30 segundos nem certifica
melhoria artística. Os parâmetros continuam exigindo revisão dos resultados.

Validação MCP dos 28 grafos: 20 passaram; oito templates experimentais têm
dependências ou ligações parciais ausentes. O grafo de Leon de 30 segundos
passou no preflight. Após a mensagem direta `Aprovado`, as duas âncoras exibidas
foram vinculadas por SHA-256 e o take Master foi submetido pelo MCP
(`bf3c1214-60ef-489f-a3d9-b49659c3bb3c`). Essa primeira tentativa foi rejeitada
pelo QC técnico: todos os quadros amostrados eram ruído cinza; a ausência de
rostos fez o detector retornar corretamente zero. Original e relatório estão
preservados. A aprovação das âncoras não aprova o vídeo. Detalhes em
`receipts/verification.json`.

## SageAttention em sequências longas

A sequência de 30 segundos em 1344×768 cria views Q/K/V cujo intervalo de
endereços supera uint32 no kernel CUDA de quantização Sage. A reprodução
`050a0433-c1ee-474f-9ab7-df3806c536ef` confirmou erro nas escalas originais e
erro zero depois da compactação. O teste completo RMSNorm/RoPE/Sage com V
constante também retornou exatamente o valor esperado e somente valores finitos.
Isso verifica kernels e memória; não certifica qualidade artística do vídeo.

O nó `PemaraH3SageLongSequencePatch` compacta grupos independentes de cabeças
antes da normalização e da quantização, mantendo o contexto temporal completo,
BF16 e SageAttention. Sequências curtas usam a função original. Não há troca de
motor, atenção nativa ou redução de resolução/steps. O código fica no plugin
local e os kernels e pesos de terceiros permanecem preservados.

O grafo de nova tentativa `2ae78cb0-1284-4306-9d7b-3dceea4da644` mantém
1344×768, 20 steps, 736 frames, áudio nativo, âncoras e seed aprovados. Salva
latentes para recuperação independente. Está EM GERAÇÃO; não é vídeo aprovado.
Os templates e o handler incluem a proteção no caminho H3 Sage. A implantação
do handler atualizado só entra em novas submissões após restart MCP com fila
ociosa; o render corrente já possui o nó explícito. Oito testes de contrato e
os 28 preflights MCP foram verificados: 20 passaram, oito falhas anteriores
persistem. Evidência em `receipts/sage_guard_preflight.json` e no projeto,
`qc/sage_long_sequence_correction.json`.
O conjunto adicional do Maestro passou em 149 testes (Face Refine, workflow,
controle de geração e jobs). O teste de preview agora verifica explicitamente
a cadeia preview → Sage → proteção → guider/scheduler.

O relatório por render conserva observações, máscaras, rastreamento, janela e
hash do original. O cálculo é feito por janelas de até 124 quadros; os quadros
de preenchimento internos são removidos, sem alterar a contagem de origem.

## Rollback

Antes de restaurar, compare o arquivo atual ao hash `after` do recibo; preserve
edições posteriores. Restaure somente arquivos cujo hash ainda corresponde à
implantação. Desative/remova o plugin recém-criado apenas com runtime ocioso,
restaure os grafos correspondentes e reinicie ComfyUI via MCP. Os backups do
backend feitos antes deste trabalho estão em `rollback/services__studio__*.py`.
Não usar reset Git: o workspace contém alterações anteriores do proprietário.

Para desligar um passe específico reversivelmente, use `enabled=false` no nó.
O handler respeita esse nó e não o duplica. Esse controle não muda o padrão
solicitado pelo proprietário.
