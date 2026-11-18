---
name: phaser-16bit-platformer
description: "Receitas condicionais para Phaser 3: boot, input, controlador, Tiled, câmera, pooling e saves. Verificar versão e ler só o tópico necessário; arquitetura usa phaser-platformer-architect."
---

# Receitas Phaser de plataforma

Confirme a versão instalada antes de usar snippets: estas receitas foram escritas para Phaser 3 e precisam de adaptação verificada em outras versões. Preserve o motor e o projeto. Não tomar exemplos como código já testado no seu runtime.

Leia somente o tópico pertinente abaixo. Para arquitetura/feel, use `phaser-platformer-architect`; não carregue os dois documentos inteiros por rotina. Preserve pixel-perfect, simulação independente de FPS, input abstrato, colisão adequada e dados versionados. Valores de movimento são pontos de partida para playtest, não regra universal.

## Receitas por necessidade

- [Tunable reference (start here, then playtest)](references/topic-01.md)
- [1. Pixel-perfect boot config](references/topic-02.md)
- [2. Framerate-independent delta (clamp the spike)](references/topic-03.md)
- [3. Input abstraction (keyboard + gamepad + buffer)](references/topic-04.md)
- [4. Full game-feel player controller](references/topic-05.md)
- [5. Tiled tilemap + solid + one-way platforms](references/topic-06.md)
- [6. Camera + parallax](references/topic-07.md)
- [7. Pooled projectiles / particles](references/topic-08.md)
- [8. Juice (cheap, pooled, optional but transformative)](references/topic-09.md)
- [9. Versioned save system](references/topic-10.md)
- [10. 60fps checklist (paste into PR description)](references/topic-11.md)
- [Gotchas that bite everyone](references/topic-12.md)

As diferenças do perfil especializado em `.agents/profiles/phaser-16bit-platformer.md` permanecem registradas; não confundir receita técnica com aprovação de arte ou controle.

## Verificação da especialidade

Confirme APIs em `phaser.d.ts` da versão instalada. Investigue delta no retorno de aba, tunneling, input no mesmo frame, deadzone, pixels fracionários e latência de áudio. Trace input → estado → velocidade → física → colisão → câmera → render. Buffer, coyote e salto variável formam um sistema; entidades transitórias devem ter ciclo de vida/pool apropriado. Entregue cenas completas e valide desempenho no alvo, escala inteira, colisão e feel em playtest. Não declare feel aprovado por headless. Defina resolução interna, Arcade/Matter, origem do mapa e plataforma quando afetarem arquitetura.
