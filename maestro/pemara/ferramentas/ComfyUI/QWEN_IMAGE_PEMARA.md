# Qwen Image no Ecossistema Pemara

Atualizado em 2026-07-06.

## Objetivo

Qwen Image entra no fluxo da Pemara para cards, anuncios, pecas com texto, layouts comerciais e edicao guiada por imagem real.

## Pacote instalado

Arquivos principais:

- `models/diffusion_models/qwen_image_2512_fp8_e4m3fn.safetensors`
- `models/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors`
- `models/vae/qwen_image_vae.safetensors`
- `models/loras/Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors`
- `models/diffusion_models/qwen_image_edit_2511_fp8mixed.safetensors`

Arquivos auxiliares obrigatorios do tokenizer:

- `comfy/text_encoders/qwen25_tokenizer/merges.txt`
- `comfy/text_encoders/qwen25_tokenizer/tokenizer.json`

O instalador fica em:

```text
E:\Pemara\maestro\pemara\ferramentas\ComfyUI\install_qwen_image_models.ps1
```

Log:

```text
E:\Pemara\maestro\pemara\dados\logs\qwen_image_install.log
```

## Quando usar

- FLUX Krea: foto realista, produto, composicao natural, render bonito.
- Qwen Image 2512: card publicitario, layout com texto, specs, chamadas, preco, titulo e portugues na arte.
- Qwen Image Edit 2511: editar uma foto real sem inventar outro produto.
- Wan 2.2: animar uma imagem pronta ou criar video depois que o frame base estiver bom.

Para Qwen Image 2512, o Maestro deve priorizar qualidade para cards e anuncios:

- padrao recomendado: sem LoRA Lightning, `40` steps, CFG/guidance `4.0`;
- use Lightning apenas para rascunho rapido, teste de layout ou geracao em lote de baixa criticidade.

Quando a LoRA Lightning for escolhida manualmente, o Studio forca a receita rapida:

- LoRA: `Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors`
- steps: `4`
- CFG/guidance: `1.0`

## Regra para loja

Para anuncio de produto, nunca depender do modelo para inventar especificacao.

Fluxo correto:

1. Foto real do produto entra como referencia/base.
2. Dados reais vem do banco/raspagem.
3. Qwen/FLUX cria a arte.
4. O sistema valida texto, marca, modelo e especificacoes.
5. So depois salva card final.

Regra de marca: o simbolo do infinito do autismo/neurodiversidade e obrigatorio na identidade Pemara quando o layout pedir marca institucional.

## Maestro

O `services/studio/main.py` foi atualizado para:

- listar modelos Qwen em `diffusion_models` como modelos de imagem;
- esconder Qwen da lista de modelos de video;
- usar workflow dedicado para Qwen Image;
- abrir Qwen 2512 em modo qualidade para cards e anuncios;
- manter 4 steps e CFG 1.0 quando a LoRA Lightning for escolhida manualmente.
- expor o modo `Card real loja`, usando Qwen Image Edit com imagem base obrigatoria;
- preparar folha de referencia 4:5 para produto real sem publicar essa folha;
- listar upscalers, ControlNet, style models e clip vision em `/api/generative/status`.

## Card real loja

Interface:

```text
Maestro -> Gerador IA -> Modo -> Card real loja
```

Padrao:

```text
1024x1280
52 steps
guidance 4.0
modelo: qwen_image_edit_2511_fp8mixed.safetensors
```

Regra: sempre anexar foto real do produto. O prompt deve conter somente texto/dados que podem
aparecer no anuncio. Produto, preco, site e especificacoes nao podem ser inventados.

Fluxo em lote:

```powershell
python E:\Pemara\marketing_social\generate_qwen_marketing_cards_max.py --dry-run --limit 3
python E:\Pemara\marketing_social\generate_qwen_marketing_cards_max.py --limit 3
python E:\Pemara\marketing_social\generate_qwen_marketing_cards_max.py --limit 3 --attempts 3
```

Status validado em 2026-07-06:

- Qwen Image Edit esta bom para acabamento visual e preservacao do produto quando usa referencia limpa.
- Ainda falha em texto critico de loja em alguns seeds: preco, site e modelo podem sair distorcidos.
- Por isso a pasta publicavel e somente `E:\Pemara\marketing_social\saida_qwen_max_aprovados`.
- Saidas em `E:\Pemara\marketing_social\saida_qwen_max_revisar` sao rascunho/rejeicao de QC.
- A opcao `--attempts` tenta novas seeds e so interrompe antes se o QC aprovar.

Depois que os pesos terminarem de baixar, reinicie o servico Studio/ComfyUI para atualizar a lista de modelos.

Smoke test executado em 2026-06-27:

- Qwen carregou no ComfyUI;
- primeira falha corrigida: tokenizer Qwen sem `merges.txt`;
- geracao 512x512 com Lightning executou de ponta a ponta, mas mostrou texto imperfeito, por isso Lightning ficou como opcao rapida e nao como padrao de qualidade.
