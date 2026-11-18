# Qwen-Image 2.1 — implantação local concluída

Data: 2026-09-22. Substitui Qwen Image 2512 e Qwen Image Edit 2511 no Maestro, incluindo edição e cartões de marketing.

- Modelo unificado INT8 ConvRot, encoder Qwen3-VL 8B INT8 ConvRot e VAE 2.1 BF16. Os três SHA-256 conferem com o repositório oficial; veja hashes.json.
- Fonte: https://huggingface.co/Comfy-Org/Qwen-Image-2.1/tree/5dc5850eb514a3685f6a03a2641728a8f7549c69
- ComfyUI atualizado de v0.36.0 para v0.37.0 no diretório existente D:/PemaraRuntimes/ComfyUI-v0.36.0-pemara. Contrato de inicialização atualizado; patch H3 preservado por hash.
- Maestro reiniciado e saudável em 127.0.0.1:8029. API confirma apenas Qwen 2.1 nos catálogos Qwen geração/edição/marketing. Preset: 40 passos, CFG 1, Euler/simple. LoRAs antigas incompatíveis não são aplicadas.
- Dois testes reais via MCP, 1024x1024: geração de bule vermelho (eb879d72-44b7-4253-b305-537022c85a50) e edição para azul (0240398e-a729-499b-9889-39db28cabecd), concluídos sem erro. Inspeção visual confirmou cor, enquadramento e rótulo. Arquivos em validation/t2i e validation/edit.
- 18 testes unitários passaram: Qwen 2.1, workflow H3 e seleção de motores de vídeo. Sintaxe Python/JavaScript validada. Resoluções maiores não foram renderizadas neste teste.
- Os dois pesos antigos e as duas LoRAs Lightning foram movidos para E:/Pemara/backups/qwen_image_21_20260922/models, fora dos diretórios de modelos ativos; veja retired_models.json. Componentes auxiliares legados foram preservados por possível compartilhamento.
- Backups do código, commit anterior e dependências estão em E:/Pemara/backups/qwen_image_21_20260922. O Qwen de linguagem não foi substituído.

## Reversão

Com a fila vazia, restaurar os quatro arquivos de retired_models.json aos caminhos originais e os backups studio_main.py (services/studio/main.py), h3_workflow.py e maestro.js aos respectivos destinos. O ComfyUI 0.37 suporta os modelos antigos. A reversão opcional do runtime exige restaurar conjuntamente o commit/dependências registrados e comfy_lifecycle.py. Reiniciar o Maestro de forma controlada sem retomar takes automaticamente.

Teste técnico não representa aprovação artística do proprietário.
