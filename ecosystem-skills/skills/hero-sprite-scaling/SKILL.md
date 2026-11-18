---
name: hero-sprite-scaling
description: >
  Ajustar/auditar o TAMANHO e a ESCALA dos heróis jogáveis de Ritmos da Revolta (Phaser).
  Resolve "idle ta menor", "ataque variando demais", "herói pequeno/grande demais", herói X
  não bate com herói Y, sprite distorcido (esticado/achatado), super puxando folha errada, e
  definir porte por arquétipo (tanker/ninja). Mede o RUNTIME real (não a auditoria), distingue
  normalização por altura-de-corpo vs escala-de-personagem, e edita os configs certos. Use
  sempre que mexer em tamanho/escala/proporção de herói. Triggers: tamanho, escala, proporção,
  idle menor, ataque variando, distorcido, body_h, cabeça, tanker, animScales, heroFrameScaleCorrections.
---

# Skill: Escala/Tamanho dos Heróis (Ritmos da Revolta)

> Origem: sessão 2026-06-22 (Wenda + Simon + Pinki/Garnold/Funbot). Antes desta skill, chegar no
> ajuste certo era sofrido porque a **auditoria mente** (mede com correções aplicadas) e o modelo
> de normalização (corpo vs personagem) não estava claro.

## REGRA DE OURO — meça o RUNTIME, nunca confie no `audit:size`
`tools/asset_pipeline/audit_hero_size_variance.py` aplica as correções e pode dizer "tudo 190 OK"
enquanto o JOGO mostra tamanhos bem diferentes. **A verdade é o que o `Player` renderiza.** Meça
via Playwright lendo `window.game.scene.getScene('StageScene').player`. Nunca diga "ajustei" sem
medir o runtime e mostrar o número (regra do projeto: verificar antes de afirmar).

## Os DOIS modelos de normalização (escolha 1 com o usuário)
1. **Altura-de-corpo fixa** (body_h = alvo): toda pose na MESMA altura. Bom pra tanker imponente
   (ex.: Simon 290) e pra quem quer "tamanho fixo". PORÉM infla poses inclinadas (run/dash têm
   corpo curto → escala sobe → cabeça grande) e encolhe poses eretas (idle) → herói parece
   "menor no idle". É o `check:sprites` clássico.
2. **Escala-de-personagem** (cabeça/porte igual; corpo varia por pose): a PERSONAGEM tem o mesmo
   tamanho em tudo; idle ereto fica naturalmente mais alto que o dash inclinado. Foi o pedido da
   Wenda ("idle menor que o dash"). Corpo NÃO é constante — alvos por-estado no `check:sprites`.

**Body_h fixo ≠ tamanho consistente.** Se o usuário diz "fulano ta menor que sicrano" comparando
poses diferentes, o problema é escala-de-personagem (cabeça), não altura.

## Mapa dos configs (onde editar)
- `js/config/index.js` → `CHARACTERS.<hero>.hitbox.animScales` = escala base por animação
  (chave = sufixo: idle/walk/run/dash/attack_1..4/attack_finisher/escape_iron_bat/special/
  backflip/hurt/pulos/pulos_up/peak/down/idle_special/dead). Runtime: `setScale(animScale × corr)`.
- `js/config/heroFrameScaleCorrections.json`:
  - `uniformFrameScaleCorrections[<hero>_<anim>]` = multiplicador POR FRAME (ambos eixos). Trava
    corpo exato (locomoção) ou =1 (pose respira).
  - `uniformScaleOnly` = lista de anims que IGNORAM correção-Y → garante X=Y (mata distorção).
  - `corrections[<hero>_<anim>]` = correção só-Y (LEGADO; ignorada se a anim está em uniformScaleOnly).
    É a fonte clássica de distorção X≠Y.
  - `targets[<hero>]` = altura-alvo (usada por check:sprites/audit).
- `tools/check_sprites.py` → `STATE_HEIGHT_TARGETS` (alvo por estado, ex. run inclinado) e o gate
  MUST (idle/walk/run/idle_special dentro de ±12% do alvo). **ESTE é o gate, não o audit:size.**
- `js/entities/Player.js` → `_applyStandardFrameScale()`: `base=animScales[key]`,
  `sx=base×uniformCorr`, `sy=sx×Ycorr` (Ycorr=1 se em uniformScaleOnly). origin (0.5,1) = pés.

## Como MEDIR no runtime (FERRAMENTA PRONTA)
**Use a ferramenta, não reescreva o script:** `npm run serve` (noutro terminal) e depois
`npm run measure:hero <hero>` (ou `node tools/measure_hero_runtime_scale.cjs <hero> [porta]`).
Ela imprime body (altura, ignora arma) e uniformidade X=Y por animação. O código abaixo é a mesma
lógica, caso precise customizar.

Detalhes: anims só nascem após o gate de clique do BootScene; a ferramenta chama
`getScene('BootScene')._generateProceduralAssets()` + `._createAnimations()` DEPOIS das texturas
carregarem. (Heróis com PNGs fatiados — garnold/funbot — podem não montar tudo nessa chamada
forçada; nesses casos confie no `check:sprites`, que mede o asset real.)

```js
// _measure.cjs → node _measure.cjs  (SwiftShader evita context-lost no headless)
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ args:['--use-gl=angle','--use-angle=swiftshader','--ignore-gpu-blocklist'] });
  const page = await b.newPage({ viewport:{width:960,height:540} });
  const HERO='wenda';
  await page.goto('http://localhost:5173/', { waitUntil:'networkidle' });
  await page.waitForFunction(()=>window.game?.textures?.exists?.(HERO+'_walk_sheet')||window.game?.textures?.exists?.(HERO+'_dash_sheet'),{timeout:30000});
  await page.evaluate(()=>{const s=window.game.scene.getScene('BootScene');try{s._generateProceduralAssets();}catch(e){}try{s._createAnimations();}catch(e){}});
  await page.waitForFunction(h=>window.game.anims.exists(h+'_walk'),HERO,{timeout:15000});
  await page.evaluate(h=>{const g=window.game;g.scene.getScenes(true).forEach(s=>{if(s.scene.key!=='StageScene')g.scene.stop(s.scene.key);});g.scene.start('StageScene',{phase:1,hero:h,score:0,lives:3,difficulty:'normal',save:{character:h,currentPhase:1}});},HERO);
  await page.waitForFunction(()=>window.game.scene.getScene('StageScene')?.player,{timeout:25000});
  await page.waitForTimeout(400);
  const out = await page.evaluate(h=>{
    const p=window.game.scene.getScene('StageScene').player;
    function solid(){ // corpo = linhas com >=10% da massa → IGNORA arma fina erguida (machado/corrente)
      const img=p.texture.getSourceImage(),f=p.frame,fw=f.cutWidth,fh=f.cutHeight;
      const cv=document.createElement('canvas');cv.width=fw;cv.height=fh;const c=cv.getContext('2d');
      c.drawImage(img,f.cutX,f.cutY,fw,fh,0,0,fw,fh);const d=c.getImageData(0,0,fw,fh).data;
      const rm=Array(fh).fill(0);for(let y=0;y<fh;y++){let n=0;for(let x=0;x<fw;x++)if(d[(y*fw+x)*4+3]>8)n++;rm[y]=n;}
      const mx=Math.max(...rm),t=Math.max(5,mx*0.1|0);let a=fh,z=-1;for(let y=0;y<fh;y++)if(rm[y]>=t){if(y<a)a=y;if(y>z)z=y;}
      return z>=a?z-a+1:0;
    }
    const r={};
    for(const st of ['idle','walk','run','dash','attack_1','attack_2','attack_finisher','escape_iron_bat','special']){
      const k=h+'_'+st; if(!window.game.anims.exists(k)){r[st]='-';continue;}
      p.anims.play(k,true);p.anims.pause();const fr=p.anims.currentAnim.frames,B=[];let sx,sy;
      for(let i=0;i<fr.length;i++){p.anims.setCurrentFrame(fr[i]);p._applyStandardFrameScale(k);B.push(+(solid()*p.scaleY).toFixed(0));sx=+p.scaleX.toFixed(3);sy=+p.scaleY.toFixed(3);}
      r[st]={body:[Math.min(...B),Math.max(...B)],uniform:Math.abs(sx-sy)<0.01};
    }
    return r;
  },HERO);
  console.log(JSON.stringify(out,null,1)); await b.close();
})();
```
- **`uniform:false`** = distorção X≠Y (achatado/esticado) → bota a anim em `uniformScaleOnly` e
  zera a `corrections[...]` só-Y.
- Para **escala-de-personagem** (cabeça): meça o blob branco conectado (heróis de cabeça clara,
  ex. Wenda) ou a largura da faixa superior (top ~18% da massa sólida) p/ cor uniforme (Simon).
  A cabeça é o proxy de escala INDEPENDENTE de pose.

## Receitas
### A. Tornar um estado UNIFORME (tirar distorção)
Adicione `<hero>_<anim>` a `uniformScaleOnly` e ponha `corrections[<hero>_<anim>]=[1,...]`.

### B. TRAVAR locomoção num alvo exato (body fixo)
`animScales.<anim> = alvo/median(source_solid)`; `uniformFrameScaleCorrections = alvo/(solid_i×base)`
por frame. (idle/walk/run/idle_special = MUST no check_sprites.)

### C. POSE que respira no porte certo (ataque/escape/special/pulo/dash)
`animScales.<anim> = alvo/median(solid)`, correção por-frame = **1** (não achatar — senão o frame
agachado/erguido distorce). Em `uniformScaleOnly`.

### D. Ataque "do mesmo tamanho" (pedido comum)
Travar body por frame a um valor (ex. Wenda 245) com correções `alvo/(solid_i×base)`. Aviso: o
frame de arma erguida encolhe um pouco. Se as poses variam MUITO (Simon: agachado 191 vs alto 306),
NÃO trave — distorce; deixe respirar (C) e explique.

### E. Frame desenhado em ESCALA ERRADA na fonte (não é pose)
Ex.: Wenda morte f3-f5 desenhados ~2,3× maiores (cabeça 99-115 vs 48). Conserto = **recompor o PNG**
(encolher os frames errados, re-ancorar bottom+centro-x, LANCZOS), não correção runtime. Depois um
`animScale` único limpo.

### F. Re-escalar o PORTE de um herói já-uniforme (ex.: Pinki 244→250)
Multiplique TODOS os `animScales` do herói por `novo/antigo`; atualize `targets[hero]` e
`STATE_HEIGHT_TARGETS[(hero,'run')]` (×razão). **Pegadinha:** regex de chave precisa cobrir dígito
(`attack_1..4`) — `[A-Za-z0-9_]+`, senão os ataques ficam pra trás.

### G. Super/efeito puxando folha errada
Confira em `BootScene._createAnimations` qual sheet o `<hero>_special` usa
(`generateFrameNumbers('<sheet>')`). Ex.: Wenda usava `wenda_ataque_fuga_sheet` em vez de
`wenda_super_sheet`. Ajuste o frameRate p/ casar com o timing do efeito (labareda/feixe em ms).

## Checklist de saída
1. `npm run check:sprites` → **GATE PASS** (não o audit:size).
2. Runtime medido: locomoção no alvo, `uniform:true` em tudo, poses no porte certo.
3. `0 erros` de console no Playwright.
4. Entrada no `FIXLOG.md` (data | arquivo | problema | causa raiz | correção | verificação).

## Porte do elenco (2026-06-22, referência)
Oren 172 < Wenda 190 (escala-de-personagem) < Garnold 235 < Pinki 250 < Funbot 260 < Simon 290 (tanker).

## Chefes = BRUTAMONTES (2026-06-23)
Chefes/sub-chefes têm de superar CLARAMENTE o herói mais alto (Simon 290). Config em
`js/config/visualScaleTargets.js`: `STANDARD_BOSS_BODY_HEIGHT_TARGET=340` (~1.17× Simon),
`BOSS_BODY_HEIGHT_TARGETS[<key>]` por-boss (raddy 360, tree 360, sun 340), `TENEBRA=360`.
`getBossBodyHeightTarget(key)` lê o mapa (fallback no padrão) e CLAMPA no teto.
**Teto prático (base 1920×1080, faixa caminhável floorTopY=831..floorBottomY=1060):**
`BOSS_BODY_HEIGHT_CEILING=440` (humanoide; cabeça nunca corta em nenhum ponto da faixa) e
`TALL_BOSS_BODY_HEIGHT_CEILING=480` (árvore/corpo estreito). NÃO passar disso senão a cabeça
encosta no HUD/topo. Raddy usa alturas-fonte por anim (`_syncRaddyF2Scale`) → o alvo novo propaga.
**Meça com `node tools/measure_boss_runtime_scale.cjs <boss_key>`** (espelha o measure de herói).
