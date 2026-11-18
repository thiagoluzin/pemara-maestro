---
name: pemara-messenger-turbo
description: "Seleciona as skills e perfis canônicos por domínio e fase; mantém o registro e a compatibilidade dos aliases. Use para escolher especialistas ou coordenar trabalho entre domínios."
---

# Pemara Messenger Turbo

É a fonte única de decisão de roteamento. O perfil `agents-turbo` é sua entrada de compatibilidade; não volte a carregá-lo depois de entrar por ele. Para inventário/manutenção, encaminhe a `pemara-ecosystem-orchestrator`, que retorna a este registro para seleção operacional.

## Seleção

1. Identifique objetivo, projeto, stack, fase e escopo já autorizado. Uma tarefa simples pode ir diretamente ao especialista pertinente.
2. Consulte [routing-map.md](references/routing-map.md) somente no domínio necessário. Carregue até três skills primárias por fase, acrescentando gates obrigatórios quando aplicáveis; troque o conjunto conforme a fase avança.
3. Leia integralmente a skill selecionada. Abra referências apenas pelos gatilhos declarados. O [método comum](references/operating-contract.md) é lido uma vez no contexto, sem copiar seu conteúdo para cada papel.
4. Consulte [turbo_registry.json](references/turbo_registry.json) para resolver aliases. Perfis especializados têm instruções próprias e permanecem distintos; não os converta por similaridade de nome.
5. Conhecimento instalado não é autorização para usar GPU, instalar, gerar mídia, publicar ou criar subagentes. Preserve as escolhas do usuário e a precedência do AGENTS.

## Domínios com contratos próprios

- Vídeo novo, direção e revisão começam com `pemara-video-production-lead`; atuação, fotografia, combate e montagem entram por fase. Use seu contrato de qualidade e o AGENTS vigente. H3 com Sage + Spectrum e acabamento obrigatório continuam obrigatórios; não usar LTX/fallback.
- Mudança em fronteira de confiança online exige `pemara-online-security-guardian`. Técnicas de hardening, scanner e revisão não substituem evidência de liberação.
- Instalação/migração/limpeza usa o especialista da stack, inventário, escopo e rollback. NVIDIA/TAO/NeMo/Jetson só quando essa stack é pertinente ao pedido.
- HyperFrames pertence a composições dessa stack; seu `general-video` não substitui a rota H3 do Maestro. Preserve o motor de cada projeto de jogo.

## Manutenção do registro

Compare conteúdo e semântica, preserve diferenças especializadas e backups. Após alterações, execute `scripts/audit_turbo_registry.py` e o inventário em `pemara-ecosystem-orchestrator/scripts/skill_inventory.ps1`. Relate aliases, especializações, erros e limites de verificação. Não chame validação estrutural de qualidade demonstrada.

## Produção musical — Qwen 3.8


Comece com `pemara-music-production-lead`; use `pemara-music-arranger`,
`pemara-music-mix-engineer` e `pemara-music-listening-qc` conforme a fase.
Qwen 3.8 é o coordenador local de letra, duração escolhida pelo modelo, estilo e plano de produção.
Na adaptação, preserve fonte, canto e identidade musical. Plano textual e QC técnico não aprovam
qualidade artística. Esses papéis não autorizam subagentes, nova mídia ou troca de motor.
