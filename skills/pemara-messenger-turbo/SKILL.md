---
name: pemara-messenger-turbo
description: Roteador canônico para consolidar skills e agentes sem duplicar políticas.
---

# Pemara Messenger Turbo

Centralize o roteamento sem copiar políticas operacionais entre skills e
perfis.

## Contrato

1. Classifique a tarefa em segurança, vídeo, imagem, áudio, jogo, frontend,
   backend, infraestrutura, automação, QA ou documentação.
2. Escolha a skill canônica mais específica em `skills/<nome>/SKILL.md`.
3. Carregue no máximo três skills primárias por tarefa, salvo gate obrigatório.
4. Trate `aliases` no registry como pontes; a instrução vive somente na skill
   canônica.
5. Use `agents/agents-turbo.md` quando a tarefa for multidomínio.
6. Preserve `specialized_profiles`: diferença semântica não é duplicata.

## Consolidação

- Compare SHA-256 e responsabilidade semântica.
- Conteúdo idêntico vira alias para uma única fonte de verdade.
- Conteúdo diferente com nome parecido permanece como especialização.
- Não escolha motor, fallback, gasto, publicação ou exclusão sem autorização.
- Mudanças de superfície pública exigem um gate de segurança independente.
- Jobs de GPU exigem inventário, lease, fila vazia e autorização atual.

Execute `scripts/audit_turbo_registry.py` após qualquer alteração no registro.
