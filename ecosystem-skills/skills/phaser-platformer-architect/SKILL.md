---
name: phaser-platformer-architect
description: "Dirige arquitetura, game feel e qualidade de jogos Phaser conforme versão, gênero e estética existentes; usa referências por decisão, sem migrar outros motores."
---

# Arquitetura e qualidade de jogos Phaser

Leia `E:/Pemara/.agents/skills/pemara-messenger-turbo/references/operating-contract.md` uma vez por contexto.

Confirme Phaser e APIs no `package.json`/lockfile e código real. Use somente em projeto Phaser; preserve outro motor já escolhido. Não assumir Phaser 3.60, data de lançamento ou facilidade de migração a partir de um exemplo antigo.

Defina gênero e estética: plataforma, run-and-gun e beat-em-up 2.5D têm física diferente; retro puro e HD Remix têm composição diferente. Preserve controles/feel aprovados e dados de configuração.

## Método

1. Leia a referência abaixo cujo título corresponde à mudança; configuração, controlador, arquitetura e arte são módulos separados. Não carregar todas.
2. Para plataforma: conferir buffer/coyote/altura variável quando previstos, aceleração/recuperação, hitboxes e one-way/tunneling no runtime. Valores são calibrados na resolução do projeto e por playtest.
3. Em 2.5D, Y de profundidade não deve receber empurrão vertical indevido por colisão de corpos; use a referência específica de beat-em-up e valide limites contra o chão visível.
4. Preserve pixel nítido, escala/câmera apropriadas, tempo independente de FPS e alocação controlada no hot path. Orçamento vem do projeto, medido no alvo e pior cenário pertinente.
5. Separe técnica de sensação de controle: testes/headless não aprovam diversão, arte, controller feel ou áudio. Entregue evidência e pendências reais.

## Referências por decisão

- [🔥 THE ABSURD CRITICAL SENSE (your defining trait)](references/topic-01.md)
- [📐 16-BIT DOCTRINE (this is a discipline, not nostalgia)](references/topic-02.md)
- [🎮 PHASER MASTERY (verify version first — patterns below are Phaser 3)](references/topic-03.md)
- [🕹️ GAME-FEEL BIBLE — the player controller that earns the 8 seconds](references/topic-04.md)
- [👊 2.5D BEAT 'EM UP DOCTRINE (Golden Rules for Brawlers)](references/topic-05.md)
- [🏗️ COMPLEX-GAME ARCHITECTURE (this scales past one screen)](references/topic-06.md)
- [⚡ 60FPS BUDGET ENFORCEMENT](references/topic-07.md)
- [🚫 PHASER-PLATFORMER ANTI-PATTERNS](references/topic-08.md)
- [🤝 Interaction with Other Agents](references/topic-09.md)
- [When You Should Be Used](references/topic-10.md)
- [✨ MODERN PIXEL ART / HD REMIX (16-bit → HD-2D)](references/topic-11.md)
- [🎓 LINEAGE OF MASTERS — o cânone que você audita contra](references/topic-12.md)
- [🏁 TURBO EXIT CHECKLIST (run before reporting complete)](references/topic-13.md)

Receitas adicionais vivem em `phaser-16bit-platformer`; animação, sprites, input e áudio têm especialistas no registro. Papéis não exigem subagentes.

## Verificação da especialidade

Confirme APIs em `phaser.d.ts` da versão instalada. Investigue delta no retorno de aba, tunneling, input no mesmo frame, deadzone, pixels fracionários e latência de áudio. Trace input → estado → velocidade → física → colisão → câmera → render. Buffer, coyote e salto variável formam um sistema; entidades transitórias devem ter ciclo de vida/pool apropriado. Entregue cenas completas e valide desempenho no alvo, escala inteira, colisão e feel em playtest. Não declare feel aprovado por headless. Defina resolução interna, Arcade/Matter, origem do mapa e plataforma quando afetarem arquitetura.
