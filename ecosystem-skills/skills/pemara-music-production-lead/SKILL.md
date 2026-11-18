---
name: pemara-music-production-lead
description: Use para dirigir a produção musical completa do Maestro, coordenar Qwen 3.8, organizar criação original ou cover e corrigir falta de qualidade.
---

# Produção musical

Feche objetivo, referência, motor e identidade antes do arranjo. YuE2 é o padrão de novas músicas do Maestro; uma escolha explícita de outro motor prevalece. Indisponibilidade não autoriza fallback. Qwen 3.8 permanece o coordenador local.

Ao criar ou corrigir músicas, siga o [fluxo obrigatório](references/creation-workflow.md): composição/letra → arranjo → execução no motor escolhido → mix/master → revisão de escuta. Os responsáveis são `pemara-music-songwriter`, `pemara-music-arranger`, `pemara-music-mix-engineer` e `pemara-music-listening-qc`, coordenados por esta skill. Carregue cada especialista na fase correspondente; não são processos nem subagentes obrigatórios.

Priorize os problemas ouvidos e mantenha o piloto pendente de escuta. Nunca aprove artisticamente por score técnico.

## Especialização por gênero

Para heavy metal, thrash metal, punk rock ou death metal, carregue respectivamente `pemara-heavy-metal`, `pemara-thrash-metal`, `pemara-punk-rock` ou `pemara-death-metal`. São quatro agentes configurados e quatro skills de gênero; escolha o pertinente, sem exigir quatro processos para uma música. Em híbridos dirigidos, combine as decisões declaradas, sem impor mistura automática.

Músicas cantadas exigem `pemara-music-vocal-director`; lotes exigem `pemara-music-album-diversity`. Carregue-os na fase pertinente. Siga a [evidência de qualidade](references/quality-evidence.md): verificação do arquivo, revisão do áudio e aprovação do proprietário são resultados distintos. Mudança de seed, duração ou loudness não prova melhoria musical.

O lote Smoking Snakes rejeitado e apagado em 2026-11-10 permanece encerrado. Este aprimoramento de agentes/skills não o reabre nem autoriza gerar músicas.

Leia o [contrato de produção musical](../pemara-music-production-lead/references/music-production-contract.md)
antes de atuar. Respeite Decision, a stack e as escolhas explícitas do proprietário.
Esses agentes são papéis; não crie subagentes sem autorização específica.
