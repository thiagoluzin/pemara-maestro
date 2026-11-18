# Atualização vinculante — 2026-09-26

A exigência de Anchor Intelligence/NVIDIA NIM foi removida por ordem do proprietário. Foto aprovada é a referência visual; não exige análise externa nem recibo. Permanecem seleção de motor, identidade, MCP/SageAttention, QC técnico e avaliação artística do vídeo. O texto abaixo é histórico e não rege mais a análise de âncoras.

# ADR-006: Seleção explícita H3/LTX 2.5, Anchor Intelligence e roteamento Turbo

## Status

Accepted

## Data

2026-09-02

## Contexto

O Maestro misturava contratos históricos de H3, LTX 2.3 e Wan, enquanto imagens-âncora de alta qualidade chegavam ao gerador de vídeo sem uma reconciliação estruturada entre o que a imagem realmente mostrava e o que o proprietário desejava animar. Isso permitia defaults implícitos, prompts genéricos e invenções do modelo. Skills e perfis de agentes também repetiam conteúdo idêntico em duas camadas.

O proprietário determinou que H3 e LTX 2.5 tenham a mesma posição na interface, que a escolha seja explícita e que não exista fallback. Determinou ainda a remoção do motor LTX 2.3, preservando somente IC-LoRAs 2.3 exigidos por workflows oficiais LTX 2.5.

## Decisão

1. O registro de motores expõe exatamente `minimax_h3` e `ltx_2_5`.
2. Todo novo take começa em `owner_selection_required`; indisponibilidade bloqueia o job e nunca troca o motor.
3. LTX 2.3 deixa de existir como engine, checkpoint, workflow, preset ou rota ativa. Apenas a allowlist `LTX25_COMPATIBILITY_ASSET` pode conter IC-LoRAs 2.3.
4. O LTX 2.5 usa o node oficial e revisão de modelo fixos, workflow API exportado e validado no ComfyUI, com prompt enhancer desativado para não reescrever o contrato da âncora.
5. `production_ready` do LTX 2.5 depende de recibo de smoke GPU; instalação e validação sem GPU produzem apenas `READY_FOR_GPU_SMOKE`.
6. Toda imagem destinada a I2V passa pelo contrato `pemara-anchor-intelligence@1`: análise visual estruturada, reconciliação com a intenção, constraints imutáveis, `DO_NOT_INVENT`, compilação específica por engine e recibo vinculado a hashes.
7. Análise visual externa é opt-in por requisição; a imagem é transitória e a saída deve obedecer ao schema. Divergência crítica bloqueia o preflight.
8. Conteúdo idêntico entre profile e skill vira alias fino `AGENTS_TURBO_ALIAS_V1`. Especialidades semanticamente diferentes permanecem independentes.
9. `Pemara Messenger Turbo` mantém o registro canônico e o roteamento; ele não executa uma skill monolítica nem amplia permissões.
10. Aprovação técnica, análise visual ou recomendação de agente nunca equivale à aprovação humana do artefato.

## Consequências

- A interface exige uma decisão clara do proprietário antes de gerar.
- Projetos legados com engine removida continuam visíveis, mas falham fechados até receberem uma seleção atual.
- O prompt fica mais longo e auditável, com menos liberdade para o gerador inventar sujeitos, objetos, texto, geometria ou câmera.
- H3 permanece produtivo; LTX 2.5 fica utilizável somente depois de seu smoke GPU explícito.
- Modos avançados que dependem de IC-LoRA ausente permanecem indisponíveis sem degradar o núcleo.
- Skills e agentes deixam de divergir por cópia, mantendo compatibilidade pelos aliases.

## Alternativas rejeitadas

### H3 como default e LTX 2.5 como fallback

Rejeitada porque mascara indisponibilidade e contraria a escolha explícita do proprietário.

### Prompt livre enviado diretamente ao gerador

Rejeitada porque não separa evidência da imagem, intenção, movimento permitido e proibições de invenção.

### Reativar todo o runtime LTX 2.3 para suportar workflows avançados

Rejeitada porque os workflows 2.5 precisam apenas de assets de compatibilidade específicos, não de um segundo motor escondido.

### Fundir todas as skills/agentes parecidos

Rejeitada porque similaridade nominal não prova equivalência comportamental; somente duplicatas exatas viram aliases.

## Evidência

- plano e inventário: `ltx25-h3-turbo-plan.md`;
- manifest de workflow: `ferramentas/video_global_engine/workflows/ltx25/manifest.json`;
- política de motores: `ferramentas/video_global_engine/policies/primary_take_orchestration_h3_ltx25.json`;
- runtime: `dados/logs/comfyui-runtime-v0342.json`;
- segurança: `E:/Pemara/logs/security_audit/maestro-ltx25-turbo-20260902/release-receipt.json`.
