# PEMARA — workflows de imagem e áudio

Pacote local para a RTX 5090, preparado em 20/09/2026. O estado verificado de cada
workflow fica em `receipts/validation.json`; existência do JSON não prova execução.

Implantação concluída: 14 workflows de interface e quatro versões API do AuK.
Os 14 arquivos instalados passaram na validação MCP, sem erros nem avisos, e
seus hashes conferem com o pacote. Os 16 arquivos safetensors novos auditados
estão estruturalmente completos; isso não equivale a aprovação artística.

## Verificação técnica

Geração concluída pelo MCP: HiDream Full (2048 × 2048, 50 passos), LLaDA Base
(50 passos), FLUX Klein (1024 × 1024), AuK Flash (voz e entrada de áudio),
YuE2 (planejamento ABC e trecho de seis segundos). Recibos e arquivos estão em
`receipts/smoke_tests.json`. O teste de edição AuK usa sinal sintético e não
comprova preservação de voz. Photoshoot, Qwen, cover/SheetSage, AuK Base e as
demais variantes têm validação estrutural; não houve avaliação artística.
audio.cpp passou em versão, carregamento CUDA e lançador sem geração; sua
inferência não foi executada nesta implantação.

## Abrir

No ComfyUI, abra a pasta `PEMARA_IMAGE_AUDIO` da lista de workflows. Os arquivos
originais deste pacote ficam em `workflows/`. Substitua os prompts e entradas de
exemplo antes de produzir. A imagem distribuída pelo LLaDA e o WAV de um segundo
são apenas entradas técnicas de demonstração, nunca referências canônicas.

No Photoshoot, o botão de série envia as oito fotos. O botão geral de execução
gera uma foto por vez; o número da foto determina sua direção dentro da série.

| Workflow | Uso |
|---|---|
| 01 HiDream Full | Âncoras-mãe; 2048 × 2048, 50 passos, variante Full BF16 |
| 02 HiDream + Photoshoot | Direção de câmera, pose e expressão; oito candidatos por lote |
| 03 LLaDA Base / Turbo | Correção por instrução; Base 50 passos, Turbo 4 |
| 04 Qwen 2512 | Texto, cartazes e layout; reutiliza os pesos locais existentes |
| 05 FLUX Klein | Rascunhos; 4B destilado, quatro passos |
| 10 YuE2 | Estilo + letra → plano ABC → música |
| 10a / 10b YuE2 | Planejar sem áudio; depois colar o ABC revisado e gerar |
| 11 YuE2 Cover | Áudio → SheetSage2 → ABC → nova versão |
| 12 AuK Base / Flash | Fala por instrução; ambiente Python separado |
| 13 AuK Base / Flash | Edição de áudio; substitua a entrada WAV de demonstração |

O AuK usa um subprocesso local com PyTorch 2.7.1/CUDA 12.8. O nó descarrega
modelos ociosos do ComfyUI antes de chamar esse ambiente, respeita cancelamento,
tem limite de execução e desativa acesso remoto do Hugging Face. Não usa Prompt
Enhancer remoto. Referência + trecho gerado devem caber em 30 segundos. PT-BR e
preservação da voz precisam de avaliação auditiva, não de aprovação por checklist.

## Continuidade e revisão

Para personagens existentes, pesquisar a versão antes de escrever a ficha.
Gerar e revisar as 3–5 âncoras-mãe antes de iniciar as séries. O workflow 02 usa
a referência original no HiDream; Photoshoot fornece somente direção. Substitua
a imagem de exemplo por uma referência aprovada. Seed fixo não comprova identidade.

Gerar em lotes de oito e revisar rosto, proporção, traje, materiais, anatomia e
composição antes de avançar. Uma nota técnica, inclusive 88/100, não aprova mídia.
Registrar a decisão humana e o SHA-256 da imagem exata no Character Registry da
produção. Rejeitados não viram referência. O pacote não inventa um crítico visual,
não promove automaticamente referências e não dispara 40 imagens ao ser aberto.

No YuE2, use `10a` para planejar sem gerar áudio. Revise o texto no Preview,
copie o ABC para o campo correspondente de `10b` e mantenha estilo/letra iguais
nas duas etapas. O gerador nativo aceita ABC vazio e desativa o planejamento;
portanto preencha esse campo para usar seu score. Isso não registra aprovação
humana automaticamente. A rota completa `10` gera plano e música na mesma execução.

## audio.cpp 0.8.1

Runtime separado em `D:\PemaraRuntimes\audio-cpp-v0.8.1`. O script
`audio_cpp_yue2.ps1` recebe arquivo UTF-8 de letra, estilo e uma pasta de saída
nova; exporta WAV e `score.abc`. `-PlanOnly` mostra os caminhos sem gerar áudio.
`-AbcFile`, `-ArLora` e `-NarLora` são entradas opcionais explícitas. Adaptadores
não são aplicados sem escolha; não há treino ou download de LoRA implícito.

## Runtime e recuperação

- Runtime novo: `D:\PemaraRuntimes\ComfyUI-v0.36.0-pemara`.
- Python novo: `D:\PemaraRuntimes\comfyui-v0360-py311`.
- Pesos novos: `D:\PemaraModels\workflows_20260920`.
- Runtime anterior preservado: `E:\Pemara\maestro\runtimes\ComfyUI-v0.34.2`.
- Estado anterior preservado: `E:\Pemara\maestro\runtimes\state\ComfyUI-v0.34.2\user`.
- Os valores anteriores de configuração MCP estão em `receipts/mcp_workspace.before.json`.

A versão 0.36 migrou a cópia do banco de assets e reconstruiu seu catálogo;
metadados manuais dessa cópia não foram migrados. O banco original e a cópia
pré-migração `.bkp` continuam preservados. Nenhuma mídia antiga foi apagada.
Para recuperar, parar pelo MCP, restaurar os três campos de configuração do
recibo, os três launchers `*.before` e a tarefa `watchdog_task.before.xml`, e
iniciar o runtime anterior pelo MCP. Não apontar a versão antiga para
o banco migrado. A escolha H3/LTX do Maestro permanece a cargo do proprietário.

O controlador `tools/comfy_lifecycle.py`, os launchers e a tarefa existente
`Pemara ComfyUI Watchdog` apontam para 0.36.0. O início pelo controlador foi
validado via MCP, com porta local e caminhos absolutos; a pausa de manutenção
da troca foi encerrada pelo próprio controlador. A tarefa legada desativada
`PemaraComfyUI` não foi ativada.

## Fontes de implantação

- https://github.com/Comfy-Org/ComfyUI/releases/tag/v0.36.0
- https://github.com/HiDream-ai/HiDream-O1-Image
- https://github.com/ralksta/ComfyUI-Photoshoot
- https://github.com/inclusionAI/LLaDA-Image
- https://github.com/T8mars/Comfyui-LLaDa-Image-T8 (adaptação comunitária AIO BF16)
- https://github.com/Tencent-Hunyuan/AuK
- https://github.com/0xShug0/audio.cpp/releases/tag/v0.8.1

Fontes consultadas em 20/09/2026. Os SHAs de código e os resultados de validação
ficam nos recibos; testes técnicos não são aprovação artística.
