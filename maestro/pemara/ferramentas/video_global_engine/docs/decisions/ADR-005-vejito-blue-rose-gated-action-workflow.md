# ADR-005: Adotar o fluxo de ação validado no Vejito Blue vs. Goku Black Rose

## Status

Accepted

## Data

2026-08-27

## Contexto

O projeto `vejito_blue_vs_goku_black_rose_3x6s_liveaction_v1` passou por rejeições de continuidade,
estilo, fusão, transformação, pose de ataque e peso do Foley. O R6 corrigido foi aprovado pelo
proprietário como o melhor projeto até o momento. O resultado não veio de um prompt único, mas de
uma sequência de gates, microsegmentação seletiva e preservação de artefatos exatos.

Copiar personagens, imagens ou prompts seria incorreto. O valor reutilizável está nas decisões de
controle e na ordem dos gates.

## Decisão

Adotar como padrão para novas sequências live action de ação no Maestro:

1. rejeição de rota para regressões sistêmicas de mundo, arte ou identidade;
2. personagens e transformações modelados como estados explícitos;
3. microtakes internos para fusões, transformações, poses técnicas e fronteiras frágeis;
4. combate bilateral com contato, deslocamento, consequência ambiental e recuperação;
5. câmera física ousada sem perda da geografia compartilhada;
6. poses icônicas vinculadas a âncoras aprovadas por hash;
7. ordem de acabamento `picture lock → RIFE → Foley → aprovação audiovisual → upscale`;
8. Foley por blocos com métricas de loudness, dinâmica e energia grave, seguido de escuta humana;
9. aprovação por artefato exato e rollback obrigatório;
10. Maestro mostrando itens de revisão, mantendo implementação interna auditável e oculta.

O documento de evidência do projeto é
`projetos/vejito_blue_vs_goku_black_rose_3x6s_liveaction_v1/docs/LESSONS_LEARNED_OWNER_APPROVED_R6_20260827.md`.

## Alternativas consideradas

### Um prompt longo por take

Rejeitada porque falhou nos beats de fusão e transformação e deixou poses técnicas ao acaso.

### Corrigir inconsistência de rota com transições editoriais

Rejeitada porque conectores não corrigem cenário, estilo ou identidade incompatíveis.

### Fazer FHD antes de aprovar o Foley

Rejeitada porque desperdiça o passe mais caro quando a trilha ainda pode exigir substituição.

### Aprovação técnica automática

Rejeitada porque decode, hashes e métricas não avaliam interpretação visual ou peso percebido do
som.

## Consequências

- Mais âncoras e gates em beats críticos, com menor custo de retrabalho tardio.
- Menos liberdade em fusões e transformações; mais liberdade controlada na pancadaria contínua.
- Uma rejeição sistêmica custa uma nova rota, mas evita montagem de fontes incoerentes.
- RIFE, Foley e upscale permanecem passes independentes, reversíveis e sujeitos a revisão humana.
- Os próximos manifestos devem materializar estes contratos; citar o ADR sem implementá-los não é
  suficiente.
