# Modeladores 3D locais — 2026-09-22

Escopo: TRELLIS.2, Hunyuan3D 2.1 e TripoSG para imagem → geometria GLB.
Pixal3D existente foi preservado. Não inclui implantação do projeto inteiro de
impressão, interface desktop, texturização PBR, fatiamento ou envio à impressora.

## Uso

No ComfyUI local, abra o workflow API do motor desejado nesta pasta e escolha
a imagem no nó LoadImage. Os novos motores usam o nó
**Maestro · Hunyuan3D 2.1 / TripoSG** (`MaestroShape3D`). TRELLIS.2 continua
usando `MaestroGame3D`. O seletor do Studio/Maestro não foi alterado nesta implantação.

- `trellis2.api.json`: TRELLIS.2, instalação existente, 512 e 12 passos.
- `hunyuan3d_2_1.api.json`: Hunyuan3D 2.1, 50 passos, octree 256.
- `triposg.api.json`: TripoSG, 50 passos, decodificador hierárquico oficial.

Os workflows apontam inicialmente para uma imagem de exemplo oficial do TripoSG.
Resultados ficam em `ferramentas/ComfyUI/output/maestro_game3d/<id>/asset.glb`.
O nó serializa a execução pela fila ComfyUI e utiliza o bloqueio de GPU do Maestro;
cancelamento encerra o subprocesso. Operação pelo Codex permanece via MCP.

## Instalação

- Runtime isolado: `D:/PemaraRuntimes/maestro-game-ai/envs/shape-modelers`.
- Código oficial: `D:/PemaraRuntimes/maestro-game-ai/apps/{Hunyuan3D-2.1,TripoSG}`.
- Pesos: `D:/PemaraRuntimes/maestro-game-ai/models/{Hunyuan3D-2.1,TripoSG}`.
- Remoção de fundo CPU: `D:/PemaraAI/model-caches/u2net/u2net.onnx`.
- Nó ativo: junction `D:/PemaraRuntimes/ComfyUI-v0.36.0-pemara/custom_nodes/MaestroShape3D`.
- Dependências exatas: `requirements-lock.txt`; `uv pip check` passou.
- Pesos baixados de revisões fixas; cinco arquivos LFS conferidos por SHA-256
  contra as fontes oficiais em `weights-verified.json`.

O TripoSG usa `use_flash_decoder=False`. A única alteração no código oficial
move o import opcional de `diso` para a função do decodificador acelerado, que
não é usada. Não houve troca do modelo nem alteração de seus pesos.
Inferência dos motores ocorre offline após instalação; não usa API paga.

## Evidência e limites

Consulte `validation/*/*.validation.json` e `deployment.json` para os jobs,
hashes das saídas e verificações. Os previews foram renderizados no Blender em CPU.
O teste comprova execução técnica; não constitui aprovação artística.
GLB sem textura não significa peça pronta para impressão. As saídas precisam de
revisão de malha, espessuras, escala física, reparo e fatiamento antes de imprimir.

## Fontes

- https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1
  — código `82920d643c0dc2f7bfd7255f45f62d386edfe60c`.
- https://github.com/VAST-AI-Research/TripoSG
  — código `fc5c40990181e2a756c4e0b1c2f4d6b5202faf8c`.
- https://huggingface.co/tencent/Hunyuan3D-2.1
  — pesos `0b94677654c57bb9a6b6845cd7b704ccf551d327`.
- https://huggingface.co/VAST-AI/TripoSG
  — pesos `2c1c516d22d58db486a058d98d31bb6177344e06`.

Para desativar os novos motores, desabilite somente o nó `MaestroShape3D` e
reinicie o ComfyUI quando estiver ocioso. TRELLIS.2/Pixal3D usam instalação e nó
separados e continuam disponíveis. Preserve pesos e saídas para reversão.
