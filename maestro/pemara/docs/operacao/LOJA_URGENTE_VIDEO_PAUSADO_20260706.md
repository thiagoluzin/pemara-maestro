# Loja urgente - video pausado

Data: 2026-07-06

## Decisao

Atividades de video ficam pausadas ate segunda ordem.

Prioridade operacional:

1. fotos originais/reais dos produtos;
2. validacao de fidelidade do produto;
3. cards e anuncios fieis;
4. loja antes de treino, render ou experimento de video.

## O que fica bloqueado

- Geracao de video no Studio (`mode=video`).
- Ferramentas de editor/remaster de video no Studio.
- Tarefa agendada `Pemara Video Studio Local Nightly`.
- Treinos/experimentos de video enquanto esta regra estiver ativa.

## O que continua permitido

- Raspagem de fotos reais da loja.
- Curadoria de candidatos.
- Geracao de imagem e edicao de foto para cards.
- Qwen/FLUX para imagem, desde que o produto real seja preservado.
- ComfyUI como servico, porque tambem serve imagem e cards.

## Regra dos cards

- Usar foto real/oficial aprovada do produto.
- Nao deixar a IA redesenhar placa, caixa, embalagem, logo, modelo ou texto tecnico.
- Texto comercial critico deve sair do banco/sistema, com validacao.
- Produto errado, mouse em lugar de pendrive, notebook em lugar de NVME, texto quebrado ou layout tipo Paint: reprovar.

## Como reativar video

Somente com ordem explicita.

1. Remover `E:/Pemara/maestro/pemara/dados/flags/video_generation_paused.flag`.
2. Reativar a tarefa `Pemara Video Studio Local Nightly`, se desejado.
3. Reiniciar o Studio 8029.
4. Registrar o motivo da reativacao.
