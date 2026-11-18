---
name: claude-context-audit
description: >
  Auditoria e otimização de uso de tokens no Claude Code. Use esta skill SEMPRE que o usuário mencionar:
  limite de uso, quota, tokens, CLAUDE.md pesado, custo alto, Claude lento, sessão esgotando,
  "atingi o limite", "gastei muito crédito", hooks, MCPs ativos demais, skills desnecessárias,
  cache miss, pensamento estendido, histórico longo de conversa, ou quiser auditar a eficiência
  do seu ambiente Claude Code. Também ative quando o usuário perguntar como reduzir consumo,
  como deixar o Claude mais rápido, ou mencionar qualquer um dos 9 padrões de desperdício.
---

# Claude Context Audit Skill

Baseado em análise empírica de 430 horas / 6 milhões de tokens de uso real do Claude Code,
73% do consumo típico vem de 9 padrões invisíveis de overhead — não de prompts ruins.

Esta skill guia a auditoria e correção desses padrões.

---

## Os 9 Padrões de Desperdício (por impacto)

| # | Padrão | % do total | Correção rápida |
|---|--------|-----------|-----------------|
| 1 | CLAUDE.md inchado | ~14% | Manter < 1.200 palavras combinadas |
| 2 | Releitura do histórico | ~13% | Sessões < 20 mensagens; usar /compact |
| 3 | Injeções de hooks excessivas | ~11% | Auditar UserPromptSubmit; manter <= 1 hook |
| 4 | Cache miss na retomada | ~10% | "Ping" em < 4 min; cache de 1h em planos pagos |
| 5 | Skills carregadas sem necessidade | ~7% | Manter 3-4 skills; desativar o resto |
| 6 | MCPs "só por precaução" | ~6% | 3 MCPs sempre ativos; resto por sessão |
| 7 | Pensamento estendido em tarefas simples | ~5% | Desligar por padrão; ativar com Alt+T |
| 8 | Geração na direção errada | ~4% | Cmd+. / Ctrl+. nos primeiros 5s |
| 9 | Hooks SessionStart redundantes | ~3% | Auditar; remover notificações de "carregado" |

---

## Fluxo de Auditoria

### Passo 1 - Rodar o script de diagnóstico

```bash
#!/bin/bash
# Salve como claude-audit.sh e rode na raiz do projeto
echo "=== CLAUDE.md size ==="
wc -w ~/.claude/CLAUDE.md 2>/dev/null
wc -w .claude/CLAUDE.md 2>/dev/null
echo "Meta: combinado < 1.200 palavras"
echo; echo "=== Hooks ativos ==="
cat ~/.claude/settings.json 2>/dev/null | jq '.hooks // {} | keys'
cat .claude/settings.json 2>/dev/null | jq '.hooks // {} | keys'
echo; echo "=== Injeções UserPromptSubmit ==="
cat ~/.claude/settings.json 2>/dev/null | jq '.hooks.UserPromptSubmit'
echo; echo "=== Hooks SessionStart ==="
cat ~/.claude/settings.json 2>/dev/null | jq '.hooks.SessionStart'
echo; echo "=== MCPs conectados ==="
cat ~/.claude/settings.json 2>/dev/null | jq '.mcpServers // {} | keys'
echo "Meta: 3 sempre ativos"
echo; echo "=== Plugins instalados ==="
ls ~/.claude/plugins/ 2>/dev/null
echo "Meta: 3-5 ativos"
echo; echo "=== Skills instaladas ==="
ls ~/.claude/skills/ 2>/dev/null
echo "Meta: 3-4 ativas que você usa todo dia"
```

### Passo 2 - Interpretar os resultados
Para cada item sinalizado, aplicar a correção correspondente abaixo.

---

## Correções Detalhadas por Padrão

### Padrão 1 - CLAUDE.md inchado
**Sintoma:** `wc -w ~/.claude/CLAUDE.md` > 1.200 palavras combinadas.
**Ação:** mover regras de framework para `.claude/CLAUDE.md` do projeto; extrair padrões repetidos para skills; deletar regras esquecidas; converter explicações longas em imperativos de 3 palavras. **Meta:** < 900 global, < 300 projeto.
**Impacto:** redução de ~31% no custo base por turno.

### Padrão 2 - Histórico de conversa longo
**Sintoma:** sessões com > 20 trocas.
**Ação:** editar mensagem anterior em vez de follow-up; ao passar de 20, pedir resumo e abrir novo chat com o resumo; usar `/compact` (não `/clear`).
**Matemática:** na mensagem 30, cada turno paga 30x o custo da mensagem 1.

### Padrão 3 - Hooks de injeção em todo prompt
**Sintoma:** `.hooks.UserPromptSubmit` > 1 hook.
**Ação:** manter só hooks justificáveis para TODA tarefa (ex.: git branch). Eliminar resumos de memória, snapshots, contexto genérico. `/plugin disable <nome>`.
**Impacto:** até 5.800 tokens por prompt.

### Padrão 4 - Cache miss na retomada
**Sintoma:** pausas > 5 min entre mensagens.
**Ação rápida:** "ping" curto antes de pausar (janela < 4 min). **Definitiva (pago):** cache de 1h (escrita 2x base uma vez; leitura 0,1x base; compensa com 10+ retomadas).

### Padrão 5 - Skills carregadas desnecessariamente
**Sintoma:** > 5 skills ativas.
**Diagnóstico:** `grep -h "skill_invoked" ~/.claude/logs/*.log | sort | uniq -c | sort -rn`
**Ação:** skill sem uso em 7 dias -> `/plugin disable`. **Meta:** 3-4. **Custo:** 800-2.500 tokens por tarefa "só por precaução".

### Padrão 6 - MCPs sempre conectados
**Sintoma:** > 3 MCPs no `mcpServers`.
**Ação:** `/mcp`, `/mcp disable <servidor>`; remover do autoload em `settings.json`. **Meta:** 3 core. **Custo:** ~600 tokens de schema por requisição.

### Padrão 7 - Pensamento estendido global
**Ação:** desligar por padrão; ativar por mensagem com **Alt+T**. ~80% das tarefas não precisam.

### Padrão 8 - Geração na direção errada
**Ação:** **Cmd+.** / **Ctrl+.** interrompe na hora (mantém o já escrito). No terminal: **Esc duplo** -> checkpoint scroller. Treinar reflexo de interromper em 5s.

### Padrão 9 - Hooks SessionStart redundantes
**Ação:** remover notificações de "carregado". **Meta:** máx 2 (branch + env críticas).

---

## Checklist Semanal
- [ ] CLAUDE.md global < 900 / projeto < 300
- [ ] Sessões média < 20 mensagens
- [ ] UserPromptSubmit <= 1 ; SessionStart <= 2
- [ ] MCPs sempre ativos <= 3 ; Skills <= 4 (todas usadas na semana)
- [ ] Pensamento estendido desligado ; Cache 1h ligado (se pago)

## O que NÃO funciona (contra-evidência)
- Trocar p/ Haiku: ~3% só. O problema é overhead de contexto, não o modelo.
- `/clear` agressivo: perde contexto; prefira `/compact`.
- Desativar todas as skills: você redigita as mesmas instruções; gasto líquido maior.
- Usar fora de pico: ~7% dos usuários; não é a alavanca principal.

## Referência de Impacto
```
Tokens produtivos antes: ~27%   ->   após as 9 correções: ~65%
```
