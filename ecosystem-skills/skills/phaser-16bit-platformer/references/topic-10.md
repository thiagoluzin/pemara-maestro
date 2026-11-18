# Referência de phaser-16bit-platformer

Aplicar apenas à versão/gênero confirmados. Valores e snippets são referências a verificar no projeto, não implementação executada nesta manutenção. Contrato específico do proprietário prevalece sobre números ilustrativos.

## 9. Versioned save system

```js
const SAVE_KEY = 'mygame_save';
function save(state) {
  localStorage.setItem(SAVE_KEY, JSON.stringify({ v: 2, ...state }));
}
function load() {
  const raw = localStorage.getItem(SAVE_KEY);
  if (!raw) return defaultState();
  let d = JSON.parse(raw);
  if (d.v === 1) d = migrateV1toV2(d);   // never trust an old schema blindly
  return d;
}
```

---

