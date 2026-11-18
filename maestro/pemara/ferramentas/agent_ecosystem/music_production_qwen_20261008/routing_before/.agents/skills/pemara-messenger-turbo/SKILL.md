---
name: pemara-messenger-turbo
description: "Roteador e registro canônico do ecossistema Pemara. Use quando uma tarefa atravessar vários domínios, quando for necessário escolher skills/agentes, consolidar instruções duplicadas, criar ou atualizar agentes, ou auditar se aliases continuam apontando para uma única fonte de verdade."
---

# Pemara Messenger Turbo

## Produção de vídeo — rota vigente

Pedido para criar, melhorar ou corrigir a qualidade de um vídeo começa com `pemara-video-production-lead`, que fecha a sequência e direciona as fases. Atuação: `pemara-performance-director`; fotografia: `pemara-cinematography-director`; montagem: `pemara-film-editor`. Esses papéis não exigem subagentes. Carregue no máximo três skills primárias por fase, além dos gates obrigatórios, trocando o conjunto conforme o trabalho avança.

O Maestro usa MiniMax H3; LTX foi removido pelo proprietário. Não escolher motor/provedor alternativo. Acabamento atual: SeedVR2 3B int8 → RIFE 4.25 j/60 → DLSS 5 Natural com áudio existente copiado. As políticas antigas de motor/acabamento em referências históricas não são instrução para novas produções.

Centralize o roteamento sem copiar políticas operacionais entre skills e perfis.

## Contrato

1. Classifique a tarefa em um ou mais domínios: segurança, vídeo, imagem, áudio, jogo, frontend, backend, infraestrutura, automação, QA ou documentação.
2. Escolha a skill canônica mais específica em `E:/Pemara/.agents/skills/<nome>/SKILL.md`.
3. Carregue no máximo três skills primárias por tarefa. Use mais apenas quando um gate obrigatório exigir.
4. Trate perfis listados como aliases em `references/turbo_registry.json` como ponte de compatibilidade. A instrução operacional vive somente na skill canônica.
5. Use `E:/Pemara/.agents/profiles/agents-turbo.md` como dispatcher quando a tarefa for multidomínio ou pedir coordenação de agentes.
6. Preserve perfis especializados listados no registro: eles têm regras diferentes da skill homônima e não podem ser substituídos automaticamente.

## Regras de roteamento

- Mudança em superfície pública, autenticação, autorização, upload, webhook, gateway, túnel, banco ou segredo exige `pemara-online-security-guardian`.
- Produção cinematográfica baseada em âncora usa `pemara-cinematic-take-director` e `pemara-video-motion-director`; análise da imagem deve preceder a compilação do prompt.
- Instalação, migração ou remoção de runtime/modelo usa a skill técnica específica e exige inventário, backup verificado e rollback.
- Tarefa simples de um domínio não deve virar uma orquestração artificial.
- Não escolha motor, provedor, fallback, gasto ou publicação em nome do proprietário quando a escolha não estiver autorizada.

## Consolidação

Ao criar ou atualizar skill/agente:

1. Compare conteúdo por SHA-256 e também por responsabilidade semântica.
2. Se o conteúdo for idêntico, mantenha a skill como fonte canônica e transforme o perfil em alias.
3. Se nomes forem iguais mas as regras diferirem, preserve ambos e registre a diferença como especialização.
4. Nunca apague uma especialização apenas por compartilhar nome.
5. Execute `scripts/audit_turbo_registry.py` após qualquer mudança no catálogo.
6. Execute também o inventário do `pemara-ecosystem-orchestrator` antes de declarar concluído.

## Saída esperada

Informe sempre: domínio detectado, skill(s) canônica(s), gates adicionais, perfil especializado preservado quando houver e evidências de validação. Não replique o texto inteiro das skills no relatório.
