---
name: pemara-ecosystem-orchestrator
description: "Audita e mantém o catálogo Pemara: inventário, aliases, versões, referências, metadados e consolidação de skills. Para selecionar especialistas de execução, usa o registro do pemara-messenger-turbo."
---

# Manutenção do ecossistema Pemara

Use `pemara-messenger-turbo` como único roteador de execução. Esta skill cuida da saúde do catálogo, sua documentação e evidências; não mantém outra árvore de seleção.

## Auditoria e mudança

1. Leia o [mapa](references/pemara-skill-map.md), o registro do Messenger e o pedido. Diferencie instalação em disco, descoberta ativa e execução real.
2. Inventarie apenas as raízes pertinentes; compare hashes, referências, versões e diferenças semânticas. Não trate nome igual ou ausência de metadados como prova de redundância.
3. Preserve backup verificável e os requisitos exclusivos antes de consolidar. Mantenha paths canônicos, especializações, motor e autorizações. Não modifique caches de plugins por fora do gerenciador.
4. Mantenha SKILL curto; referências por modo; metadados discriminantes. Use `skill-creator` ao criar ou revisar habilidades. Leitura progressiva precisa ter gatilho e caminho explícitos.
5. Execute `scripts/skill_inventory.ps1 -PemaraOnly -Validate` e `E:/Pemara/.agents/skills/pemara-messenger-turbo/scripts/audit_turbo_registry.py` após mudar o catálogo. Compare cenários de uso quando alterar roteamento/semântica; checks estruturais não avaliam qualidade artística.
6. Entregue arquivos alterados, recibo, requisitos preservados, verificações e limites. Economia de tokens/tempo depende de medição, não de contagem de bytes.

## Evidência e permissões

Leia o [método comum](../pemara-messenger-turbo/references/operating-contract.md). Para auditoria de acesso, estado de take ou runtime Maestro, leia [maestro-evidence.md](references/maestro-evidence.md). Respeite pausas e admissão atual de GPU; inventário não autoriza geração, treino, reinício ou limpeza destrutiva.

O `scripts/hubmesh_radar.py` fornece sinais públicos para pesquisa, não instalação automática. Adoção exige revisão de licença, atividade, dependências/segredos, sobreposição e verificação isolada no escopo autorizado.

## Caminhos

- Skills: `E:/Pemara/.agents/skills`; perfis: `E:/Pemara/.agents/profiles`.
- Auditorias/rollback: `E:/Pemara/maestro/pemara/ferramentas/agent_ecosystem`.
- Referências de projetos: `E:/Pemara/PEMARA_PROJECT_MAP.md`; fatos históricos não estabelecem runtime atual.

Produção musical segue o registro vigente do Messenger e `pemara-music-production-lead`, incluindo os especialistas de arranjo, mix e escuta. Preservar Qwen 3.8 como coordenador local e as escolhas de motores do proprietário; inventário não altera esse fluxo.

## Produção musical — Qwen 3.8

Comece com `pemara-music-production-lead`; use `pemara-music-arranger`,
`pemara-music-mix-engineer` e `pemara-music-listening-qc` conforme a fase.
Qwen 3.8 é o coordenador local de letra, duração escolhida pelo modelo, estilo e plano de produção.
Na adaptação, preserve fonte, canto e identidade musical. Plano textual e QC técnico não aprovam
qualidade artística. Esses papéis não autorizam subagentes, nova mídia ou troca de motor.
