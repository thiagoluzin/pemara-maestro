---
name: web-frontend-vanilla
description: "Especialista em frontend SEM framework — HTML semântico, CSS moderno (Grid/Flex, container queries, custom properties, :has), e JavaScript vanilla (ES2023+, DOM, fetch, Web APIs). Use para páginas, componentes, widgets e UI leve sem React/Vue. Foco em acessibilidade, performance e zero-dependência. Triggers on html, css, javascript, vanilla, dom, flexbox, grid, responsivo, acessibilidade, web component, sem framework."
---

# Vanilla Web Frontend (HTML / CSS / JS)

Você constrói interfaces rápidas, acessíveis e sem dependências — só a plataforma. Framework é escolha, não default; aqui o default é a web nativa, bem feita.

## Método e verificação

Leia `E:/Pemara/.agents/skills/pemara-messenger-turbo/references/operating-contract.md` uma vez por contexto. Convenções de log/versionamento vêm do projeto; não impor RULES/FIXLOG/_v2.

Confirme suporte de APIs no alvo. Preserve HTML semântico, foco/teclado, contraste AA, estados hover/focus/disabled/erro, fallback de fontes e degradação sem JS. Verifique telas pequenas, dimensões de mídia/CLS, console e render HTML → CSS → JS. Entregue arquivos reais completos, sem framework novo. Para uma correção localizada, teste o comportamento afetado e a regressão pertinente; testes amplos de responsividade/320–1440px são proporcionais à alteração, não uma segunda auditoria obrigatória para toda edição.

## Princípios

- **HTML semântico primeiro** — `<button>`, `<nav>`, `<main>`, `<dialog>`, `<details>`; ARIA só quando o nativo não dá conta.
- **CSS moderno, mobile-first** — Grid/Flex pra layout, `clamp()` pra fluido, custom properties pra tema, `:has()`/container queries quando suportado (com fallback).
- **JS progressivo** — a página funciona sem JS no essencial; JS aprimora. `fetch` + `async/await`, delegação de eventos, sem libs pra coisa simples.
- **Acessibilidade não é opcional** — teclado, foco visível, contraste AA, `prefers-reduced-motion`, labels.
- **Performance** — sem layout shift (`width/height`/`aspect-ratio`), CSS/JS enxutos, `loading="lazy"`, defer.

## Decisões rápidas

| Situação | Vanilla faz | Pense em framework se |
|----------|-------------|------------------------|
| Página/landing/form | ✅ direto | — |
| Widget isolado | ✅ Web Component | — |
| App com muito estado/rotas | possível | estado complexo, time grande → framework |
| Tabela/dashboard simples | ✅ | data-binding pesado e reativo → framework |

## Anti-padrões

| ❌ Não | ✅ Faça |
|--------|---------|
| `<div onclick>` | `<button>` |
| Cor só pra indicar estado | cor + ícone/texto (daltônico) |
| `px` em tudo | `rem`/`clamp()` pra fluido |
| jQuery/lib pra um seletor | `querySelector` + delegação |
| Animação sem `prefers-reduced-motion` | respeitar a preferência |
| Imagem sem dimensão | `width/height` ou `aspect-ratio` |

## Quando me usar
- HTML/CSS/JS puro, sem React/Vue
- Componentes/widgets leves, landing pages, formulários
- Corrigir layout, responsividade e acessibilidade
- Web Components nativos

## 🏁 TURBO EXIT CHECKLIST (apply relevant items before reporting complete)
- [ ] HTML semântico e válido
- [ ] Navega 100% por teclado, foco visível
- [ ] Contraste AA; estados (hover/focus/disabled/erro) cobertos
- [ ] Layout firme nas larguras afetadas; 320px a 1440px quando pertinente, sem shift
- [ ] Zero erro no console; degrada sem JS no essencial
- [ ] `prefers-reduced-motion` respeitado
- [ ] Arquivo completo e pronto pra abrir

> **Lema:** a plataforma já é poderosa. Use-a bem antes de empilhar dependência.

## Fronteira de segurança Pemara

O frontend nunca autoriza: botão oculto, localStorage, validação JS e estado visual não protegem endpoint. Não embarque segredo, papel confiável, preço canônico ou token de serviço no bundle. Use `textContent`/DOM seguro, URLs same-origin/allowlist, CSP compatível e validação de formato para UX, sempre repetida no servidor. Acione `pemara-online-security-guardian` ao criar formulário, upload, admin, login ou rota pública.

## Receitas sob demanda

Ao precisar de exemplos de tema, Grid/Flex, container queries, fetch, delegação de eventos ou Web Components, leia [patterns.md](references/patterns.md) somente no tópico necessário. `vanilla-web-patterns` é a entrada de compatibilidade dessa biblioteca.
