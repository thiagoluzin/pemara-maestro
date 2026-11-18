[⬅ Voltar ao Painel de Produção](../00_PAINEL.md)

---

## PARTE 1: SPRITES DOS HERÓIS

### COMO USAR ESTA PARTE

O Oren (herói de referência) tem **11 animações separadas**, cada uma num arquivo próprio. Os prompts abaixo seguem essa mesma estrutura. **Nunca pedir múltiplas animações num strip só** — cada prompt gera um arquivo, que corresponde a uma pasta na engine.

| Arquivo gerado | Pasta na engine | Frames |
|---|---|---|
| `[heroi]_idle.png` | `idle/` | 7 |
| `[heroi]_walk.png` | `walk/` | 8 |
| `[heroi]_ataques.png` | `ataques/` | 8 |
| `[heroi]_ataque_fuga.png` | `ataque_fuga/` | 4 a 9 conforme regra |
| `[heroi]_dash.png` | `dash/` | 6 minimo |
| `[heroi]_esquiva.png` | `esquiva/` | 4 |
| `[heroi]_dano.png` | `dano/` | 3 |
| `[heroi]_morte.png` | `morte/` | 6 |
| `[heroi]_pulo.png` | `pulos/` | 5 |
| `[heroi]_super.png` | `super_art/` | 6 |
| `[heroi]_tedio.png` | `super_art/tedio/` | 6 |

> **REGRA OBRIGATORIA DE IDLE/DASH:** ver [`../../REGRA_OBRIGATORIA_IDLE_DASH.md`](../../REGRA_OBRIGATORIA_IDLE_DASH.md). Idle deve ter minimo 7 frames com respiracao/overlap real. Dash de heroi jogavel deve ter minimo 6 frames; dash de 4 frames e legado/placeholder e nao deve ser aprovado como corrida/dash final.

> **REGRA OBRIGATORIA DE ATAQUE DE FUGA:** ver [`../../REGRA_OBRIGATORIA_ATAQUE_FUGA.md`](../../REGRA_OBRIGATORIA_ATAQUE_FUGA.md). Oren e a referencia aprovada de feeling; Pinki e Wenda usam original_9f recomposto dos frames reais do proprio heroi; Simon e Funbot usam raw_fuga_9f das folhas cruas especificas de fuga; Garnold usa energy_ball_burst_6f por prompt original e referencia visual aprovada. Nao alterar tamanho, baseline ou contrato do runtime sem atualizar BootScene, check_sprites e auditoria.

**Regras universais:**
- 128×128 pixels por frame, strip horizontal
- Fundo `#00FF00` obrigatório
- **Espaçamento: deixe um gap LARGO de verde neon entre cada frame — frames bem separados, sem encostar/sobrepor, cada um isolado com padding em volta.** Ajuda o gerador a não fundir frames e facilita o recorte. (Os "Total" de cada prompt são o tamanho de conteúdo nominal; com os gaps a largura final fica maior — tudo bem, o sheet é remontado depois.) **Crítico para quem usa corrente/arma comprida (ex.: Wenda).**
- Estilo 16-bit SNES (Final Fight 3 / Streets of Rage 4)
- Sem anti-aliasing. Mesma baseline em todos os frames.
- Iluminação do canto superior esquerdo.

> **OREN:** Sprites já existem na pasta `assets/sprites/herois/oren/`. Usar como referência visual para todos os outros.

---

