# Melhorias H3 implantadas — 27/09/2026

O VAE INT8 ConvRot passou a ser o padrão dos novos workflows H3 construídos pela rota principal do Studio/Maestro. O Studio foi reiniciado pelo controlador existente. SageAttention continua obrigatório e foi confirmado no transformer dos quatro renders de validação.

PDD FL2VA, PDD Ref2VA e ControlNet Union 2.0 foram instalados e disponibilizados como workflows separados. PDD não virou padrão e não foi combinado com ControlNet. O seletor H3/LTX e os projetos anteriores permanecem preservados. Os builders Creative OS que fixam contratos anteriores de VAE não foram migrados.

## Resultado medido

Comparação sintética de encode/decode: 1088×608, 73 quadros, segunda execução de cada VAE, ambos com fp16_accumulation habilitado.

| VAE | Encode | Decode | Total |
|---|---:|---:|---:|
| FP16 | 3,278 s | 2,949 s | 6,226 s |
| INT8 ConvRot | 3,445 s | 1,777 s | 5,223 s |

Redução de 39,72% no tempo de decode e 16,12% no conjunto encode/decode. PSNR entre as saídas: 56,21 dB; diferença absoluta máxima: 0,08349; valores finitos. Esse teste não mede aceleração total de geração nem prova equivalência artística em cenas reais.

## Renders reais de implantação

Todos passaram pela validação MCP antes do envio. Inputs oficiais de exemplo; áudio desativado; nenhuma produção anterior reaberta.

| Rota | Passos | Quadros | Tempo total observado | Resultado |
|---|---:|---:|---:|---|
| H3 base + VAE INT8 | 10 | 73 | 22,43 s | concluído |
| PDD FL2VA | 8 | 73 | 33,97 s | concluído |
| PDD Ref2VA | 8 | 73 | 37,07 s | concluído após corrigir a chave da referência |
| ControlNet 2.0 Pose | 40 | 124 | 213,55 s | concluído |

Tempos incluem condições distintas de carregamento/cache e não são benchmark controlado entre rotas. Neste teste o PDD não demonstrou menor tempo total que a base. Ele também mudou a trajetória da mão robótica. Mantê-lo opcional até comparação artística e desempenho com inputs do projeto.

As quatro saídas são H.264, 1088×608, 24 fps e decodificam integralmente sem erro. Inspeção de início/meio/fim mostrou materiais metálicos reconhecíveis nos testes da mão e dança no cenário de campo no ControlNet. Isso não constitui aprovação artística nem comprova fidelidade de pose quadro a quadro. Evidência em `results/media_qc.json` e nas contact sheets.

31 testes direcionados passaram: 12 do workflow H3, 13 do lifecycle e 6 do Studio. O teste fornecido pelo PDD também passou nos casos executáveis, com casos dependentes de modelos/runtime dispensados; os renders acima verificaram o carregamento real FL2VA e Ref2VA.

## Como usar

No ComfyUI, abrir os workflows salvos em `PEMARA_H3_UPGRADES`:

- `01_H3_BASE_INT8_VAE.json`: base de 10 passos.
- `02_H3_PDD_FL2VA_8STEP.json`: PDD específico FL2VA, Euler e sigmas treinados.
- `03_H3_PDD_REF2VA_8STEP.json`: PDD específico Ref2VA, com referência.
- `04_H3_CONTROLNET2_POSE.json`: Pose com Union 2.0, sem PDD.

Os quatro templates editáveis foram validados por MCP sem erros/avisos. A versão API e os testes curtos estão em `workflows/`. Os templates usam exemplos oficiais e devem receber prompt e referências da nova produção antes de uso. Não são promoção automática dos testes a mídia final.

## Implementação e recuperação

- Runtime ativo: ComfyUI 0.37.0 em `D:\PemaraRuntimes\ComfyUI-v0.36.0-pemara`; o nome da pasta não identifica a versão instalada.
- VAE, dois PDDs e ControlNet baixados por MCP; SHA-256 em `receipts/model_hashes.json`.
- Node PDD fixado no commit `311a65dd53832d8a5f8177a9d5fb923c09e35a90`.
- Correções ControlNet aplicadas apenas nos três arquivos do patch oficial PR 16471; sem atualização geral do runtime.
- Acrescentado `--fast fp16_accumulation` ao lançamento central. Criado node local de benchmark VAE.
- Corrigida a junction de downloads quebrada, preservando-a como `.comfy-downloads.before_h3_20260927`.
- VAE FP16 anterior mantido. Um link de arquivo no catálogo legado aponta para o novo VAE em D:, sem duplicar o modelo em E:.

Snapshots anteriores estão em `rollback/`. Para reverter, comparar os arquivos atuais aos snapshots e desfazer apenas os trechos desta implantação, preservando alterações concorrentes/preexistentes. Repor o VAE FP16 nas constantes do Studio e retirar os dois argumentos adicionados ao lifecycle se desejado. Reverter o patch ControlNet usando `receipts/controlnet2_upstream.diff` após conferir conflitos. Não restaurar indiscriminadamente snapshots completos do Studio. Não excluir modelos, user state ou projetos para reverter. Reinício do ComfyUI continua pelo MCP/controlador central e somente com fila viva verificada. Backups de configuração são locais e não devem ser publicados.

Ao encerrar, o MCP confirmou fila viva sem jobs rodando ou pendentes; registros históricos antigos marcados queued não foram reenviados nem cancelados.

## Fontes

- https://blog.comfy.org/p/making-the-minimax-h3-video-vae-2x
- https://huggingface.co/Comfy-Org/MiniMax-H3
- https://huggingface.co/alibaba-pai/MiniMax-H3-Acc-LoRAs
- https://github.com/Jalen-Brunson/ComfyUI-MiniMax-H3-PDD-Acc
- https://huggingface.co/alibaba-pai/MiniMax-H3-Fun-Controlnet-Union-2.0
- https://github.com/Comfy-Org/ComfyUI/pull/16471
