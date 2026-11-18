# Skill: Padrões Vanilla Web (HTML/CSS/JS)

Sem dependência. Mobile-first, acessível, sem layout shift.

## CSS — base de tema (custom properties + reset enxuto)
```css
*,*::before,*::after{box-sizing:border-box;margin:0}
html{-webkit-text-size-adjust:100%}
img,svg,video{display:block;max-width:100%;height:auto}      /* sem overflow */
:root{
  --bg:#0f1115; --fg:#e6e7ea; --accent:#3b82f6; --muted:#9aa0a6;
  --space:clamp(.75rem,2vw,1.25rem);
  --fs:clamp(1rem,.9rem + .4vw,1.125rem);                    /* tipografia fluida */
  color-scheme:dark light;
}
body{background:var(--bg);color:var(--fg);font:var(--fs)/1.6 system-ui,sans-serif}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
```

## CSS — layout responsivo sem media query (auto-fit)
```css
.grid{display:grid;gap:var(--space);
  grid-template-columns:repeat(auto-fit,minmax(min(100%,16rem),1fr))}
```

## CSS — :has() e container query (com fallback)
```css
.card{padding:var(--space)}
@supports selector(:has(*)){
  .form:has(input:invalid) .submit{opacity:.5;pointer-events:none}  /* só se suportar */
}
@container (min-width:30rem){ .card{grid-template-columns:1fr 1fr} } /* requer container-type no pai */
.panel{container-type:inline-size}
```

## JS — fetch robusto (timeout + retry)
```js
async function getJSON(url, {tries=3, timeout=8000} = {}){
  for(let i=0;i<tries;i++){
    const ctrl=new AbortController(); const t=setTimeout(()=>ctrl.abort(),timeout);
    try{
      const r=await fetch(url,{signal:ctrl.signal});
      if(!r.ok) throw new Error(`HTTP ${r.status}`);
      return await r.json();
    }catch(e){ if(i===tries-1) throw e; await new Promise(s=>setTimeout(s,2**i*300)); }
    finally{ clearTimeout(t); }
  }
}
```

## JS — delegação de eventos (1 listener pra muitos itens)
```js
document.querySelector('#lista').addEventListener('click', e => {
  const btn = e.target.closest('[data-acao]');
  if(!btn) return;
  if(btn.dataset.acao === 'remover') btn.closest('li')?.remove();
});
```

## JS — Web Component nativo (sem lib)
```js
customElements.define('contador-clique', class extends HTMLElement{
  #n=0;
  connectedCallback(){
    this.innerHTML=`<button type="button" aria-live="polite">Cliques: <span>0</span></button>`;
    this.querySelector('button').addEventListener('click',()=>{
      this.#n++; this.querySelector('span').textContent=this.#n;
    });
  }
});
// uso: <contador-clique></contador-clique>
```

## Acessibilidade — checklist rápido
- `<button>` pra ação, `<a href>` pra navegação (nunca `<div onclick>`).
- Foco visível: `:focus-visible{outline:2px solid var(--accent);outline-offset:2px}`.
- Imagem informativa tem `alt`; decorativa tem `alt=""`.
- Form: todo input com `<label for>`; erro com texto + ícone, não só cor.
- Contraste ≥ 4.5:1 (texto normal).

## Gotchas
1. Imagem sem `width/height`/`aspect-ratio` → layout shift (CLS).
2. `:has()`/container queries: cheque suporte do alvo; use `@supports` como fallback.
3. `rem` pra escala acessível; `px` só pra bordas/detalhes.
4. JS deve aprimorar, não ser pré-requisito do conteúdo essencial.