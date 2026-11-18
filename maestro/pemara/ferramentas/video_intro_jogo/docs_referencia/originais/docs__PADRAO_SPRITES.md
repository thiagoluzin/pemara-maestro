# PADRAO DE SPRITES DOS HEROIS - regra do projeto

> Objetivo: acabar com o ciclo "testa e arruma eterno". Antes de afirmar que um sprite de heroi
> esta certo, rode o validador. Ele mede o PNG real, nao e no olho e nao e no chute.

```powershell
npm run check:sprites        # ou: py -3 tools/check_sprites.py
npm run audit:heroes         # tamanho + auditoria walk/ataques/fuga + qualidade geral
```

Sai com erro (codigo 1) se algo estiver fora do padrao. Ja roda automaticamente antes de
`npm run build:demo` (gate do .exe).

## Referencia por heroi

Nao existe mais altura unica para todos os herois. Cada heroi tem alvo proprio em
[`js/config/heroFrameScaleCorrections.json`](../js/config/heroFrameScaleCorrections.json):
Oren e baixo/forte, Pinki e a mais alta, Simon e tanker, Wenda e media-alta, Funbot e robo monge,
Garnold e cyborg jedi.

Dentro de cada heroi, porem, o tamanho precisa ser consistente. No Oren, o `run` aprovado em
`assets/sprites/herois/oren/run/oren_run_sheet.png` virou a referencia oficial de presenca visual:
os outros estados dele devem casar com essa leitura sem alterar o alvo de corpo de 172px e sem
destruir o `ataque_fuga` aprovado.

Qualquer sprite mexido precisa continuar compativel com os sprites que nao foram mexidos. Nao se
aprova uma troca que deixa o heroi crescer, encolher, subir/descer a baseline ou dar pop visual
entre `idle`, `walk`, `dash`, `attack`, `hurt`, `special` e `escape_iron_bat`.

## As 3 garantias que o validador checa

1. **Tamanho consistente.**
   Estados que se ve parado/andando - `idle`, `walk`, `run`, `idle_special` (tedio) - precisam
   ficar dentro de +/-12% do alvo do proprio heroi. Reprova se fora.

2. **Nao encolhe entre frames.**
   Num mesmo estado de locomocao, nenhum frame pode afundar mais que 18% abaixo da pose em pe.

3. **Nao duplica personagem no frame.**
   - Sheets: a imagem precisa dividir exato pelo `frameWidth`/`frameHeight` declarado no BootScene.
   - Frames de idle individuais: 1 cluster de personagem so.

### Poses de acao variam de altura de proposito

`attack`, `dash`, `backflip`, `escape_iron_bat`, `pulos`, `hurt`, `dead` e `special` mudam a
silhueta (golpe, recuo, deitado, giro, salto). O validador so avisa nesses; so reprova se estiver
grosseiramente fora (>30%). Nao normalize todos os herois para o Oren: preserve a identidade de
altura e massa definida no JSON.

## Onde ficam as escalas

As escalas por estado ficam em [`js/config/index.js`](../js/config/index.js), em
`CHARACTERS.<heroi>.hitbox.animScales`. O validador le esse arquivo (fonte unica) e mede os PNGs
em `assets/sprites/herois/<heroi>/`. Para mudar tamanho, mexe no `animScales` e roda o validador,
nunca duplica numero em outro lugar.

Metodo de calibracao das escalas:
`escala_y = alvo_de_corpo_do_heroi / (body_h_do_frame * animScaleX)`,
ancorando no alvo do proprio heroi para o frame baixo de windup/recuo nao puxar o tamanho.

Para ataques e supers, nao use correcao Y-only grande para bater a altura. Se a proporcao
`scaleY / scaleX` ficar muito longe de 1.0, o personagem vira "linguica". Nesses estados, primeiro
ajuste a escala uniforme do golpe; se ainda nao casar, gere/edite arte nova.

## Como adicionar um heroi novo ao padrao

1. Carregue os sheets em `BootScene.js` com `frameWidth/frameHeight` que dividam exato.
2. Calibre `animScales` no config pelo metodo acima.
3. Acrescente o heroi ao `MANIFEST` em [`tools/check_sprites.py`](../tools/check_sprites.py).
4. Rode `npm run check:sprites` ate passar (codigo 0).

## Regra obrigatoria de idle e dash

Idle e dash seguem regra propria em [`REGRA_OBRIGATORIA_IDLE_DASH.md`](REGRA_OBRIGATORIA_IDLE_DASH.md).
Resumo: `idle` minimo 7 frames, ideal 8 a 10; `dash` de heroi jogavel minimo 6 frames,
ideal 6 a 8. Dash com 4 frames e legado/placeholder, aceitavel apenas para esquiva curta,
golpe-fuga ou asset temporario.

## Regra obrigatoria de walk e ataques

Walk e ataques seguem regra propria em [`REGRA_OBRIGATORIA_WALK_ATAQUES.md`](REGRA_OBRIGATORIA_WALK_ATAQUES.md).
Resumo: `walk` minimo 8 frames reais; cada ataque basico minimo 3 frames com antecipacao,
impacto e recuperacao. `attack_4` e `finisher` nao podem reutilizar exatamente os mesmos
frames de `attack_3`.

## Regra obrigatoria de ataque de fuga

Ataque de fuga segue regra propria em [`REGRA_OBRIGATORIA_ATAQUE_FUGA.md`](REGRA_OBRIGATORIA_ATAQUE_FUGA.md).
Resumo: Oren e referencia aprovada e nao deve ser mexido agora. Pinki, Wenda e
Garnold usam original_9f recomposto dos frames reais do proprio heroi; Simon e Funbot
usam raw_fuga_9f das folhas cruas especificas de fuga. Qualquer
troca precisa preservar frameWidth/frameHeight, baseline, escala renderizada e compatibilidade
com os estados nao mexidos do mesmo heroi.

## Regra obrigatoria de auditoria de qualidade

Qualidade geral de movimento segue regra propria em [`REGRA_OBRIGATORIA_AUDITORIA_QUALIDADE.md`](REGRA_OBRIGATORIA_AUDITORIA_QUALIDADE.md).
Resumo: `npm run audit:quality` pega loop travado, pose repetida, idle estatua, ataque curto,
reuso de golpes e runtime accent que faz personagem crescer/engordar. Nao aprove estado mexido
se ele sair como `CRITICO` ou `REWORK`.

## Regra para bosses aprovados

Boss/subchefe aprovado por arte final nao recebe FX procedural desenhado por Python por cima do sprite.
Scripts podem apenas recortar chroma, limpar alpha, alinhar, escalar, tintar, montar frames/sheets e
gerar previews. Golpes, lasers, raios, particulas e efeitos visuais precisam vir de arte aprovada ou
de VFX runtime revisado, nunca de linhas/glows inventados no builder do spritesheet.
