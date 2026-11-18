---
name: game-audio-reactive
description: >
  Áudio de jogo como PILAR de design (linha Akira Yamaoka), não enfeite: som e silêncio que
  reagem ao estado do jogo. Receitas Phaser/Web Audio — variação de pitch pra evitar fadiga,
  ducking de música sob SFX, camadas de tensão por crossfade, filtro low-pass em pouca vida,
  hitstop sonoro, silêncio como tensão, unlock mobile. Use ao adicionar/dar vida ao áudio.
---

# Skill: Áudio Reativo de Jogo (escola Yamaoka)

**Princípio:** áudio não é trilha tocando por cima — é mecânica de clima. Som e **silêncio** carregam tensão, perigo, alívio e impacto. Reativo ao estado, sempre.

## 1. Variação de pitch — mate a fadiga de repetição
O mesmo SFX idêntico 50x soa robótico. Varie levemente:
```js
// rate muda pitch+velocidade; detune (cents) muda só o pitch
this.sound.play('hit',  { rate: Phaser.Math.FloatBetween(0.92, 1.08) });
this.sound.play('coin', { detune: Phaser.Math.Between(-120, 120), volume: 0.7 });
```

## 2. Ducking — música abaixa sob um som importante
```js
const music = this.sound.add('bgm', { loop: true, volume: 0.6 });
music.play();
function duckFor(scene, sfxKey) {
  scene.sound.play(sfxKey);
  scene.tweens.add({ targets: music, volume: 0.2, duration: 80, yoyo: true, hold: 200 });
}
```

## 3. Camadas de tensão — crossfade por estado (Silent Hill-style)
Duas (ou mais) faixas tocando juntas; o "perigo" controla o mix:
```js
this.calm   = this.sound.add('layer_calm',   { loop: true, volume: 1 });
this.tense  = this.sound.add('layer_tense',  { loop: true, volume: 0 });
this.calm.play(); this.tense.play();   // ambas rodando, sincronizadas
setDanger(d) {                          // d: 0..1
  this.calm.setVolume(1 - d);
  this.tense.setVolume(d);
}
```

## 4. Filtro low-pass em pouca vida (abafado = perigo)
Avançado — usa Web Audio direto. **Confirme os nomes dos nós na sua versão do Phaser** (Evidence Gate); a estrutura interna do WebAudioSoundManager muda entre versões.
```js
const ctx = this.sound.context;                 // AudioContext (backend WebAudio)
const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 22050;
// roteia master -> filtro -> saída (verifique masterVolumeNode/destination na sua versão)
this.sound.masterVolumeNode.disconnect();
this.sound.masterVolumeNode.connect(lp); lp.connect(ctx.destination);
// em pouca vida: fecha o filtro (abafa)
onLowHealth(t){ lp.frequency.setTargetAtTime(800, ctx.currentTime, 0.1); }
onHeal(){ lp.frequency.setTargetAtTime(22050, ctx.currentTime, 0.2); }
```

## 5. Hitstop sonoro — vende o impacto
No golpe pesado: micro-pausa + som seco grave, depois retoma.
```js
this.sound.play('impact_heavy', { rate: 0.9 });
this.physics.world.pause();
this.time.delayedCall(70, () => this.physics.world.resume());
```

## 6. Silêncio como tensão
Antes de um chefe/queda/susto: **corte** a música por 1–2s. O vazio assusta mais que estímulo.
```js
this.tweens.add({ targets: music, volume: 0, duration: 300, onComplete: () => music.pause() });
// ...no clímax: music.resume() com um stinger
```

## 7. Unlock de áudio no mobile (autoplay travado)
```js
this.input.once('pointerdown', () => { if (this.sound.locked) this.sound.unlock(); });
```

## Checklist Yamaoka (rode antes de dizer "áudio pronto")
- [ ] Cada SFX repetível tem variação (pitch/detune) — sem fadiga
- [ ] Música reage ao estado (perigo/vida/área), não toca alheia ao jogo
- [ ] Há uso intencional de **silêncio** em pelo menos um momento de tensão
- [ ] Impactos têm peso sonoro (camada grave + hitstop)
- [ ] Ducking pra sons que importam não sumirem na música
- [ ] Mobile: áudio destrava no primeiro toque
- [ ] Mix: nada estoura (clipping); SFX legível sobre a música

## Anti-padrões
| ❌ Não | ✅ Faça |
|--------|---------|
| Mesmo SFX idêntico sempre | variação de pitch/detune |
| Música ignora o jogo | reativa ao estado (camadas/filtro) |
| Áudio como última etapa | pilar desde o protótipo |
| Tudo no volume máximo | mix com ducking e headroom |
| Tensão só com mais som | usar silêncio também |
