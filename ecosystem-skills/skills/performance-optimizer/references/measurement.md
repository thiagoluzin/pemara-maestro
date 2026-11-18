# Medição antes e depois

Registre hardware/ambiente, carga/dados, versão, caminho crítico, ferramenta, unidades e repetições. Compare condições equivalentes e informe variação; não generalize uma amostra isolada.

| Sintoma | Evidência inicial |
|---|---|
| Carregamento web | Waterfall/TTFB, LCP, bundle e recursos bloqueantes |
| Interação | Long tasks/INP, operações DOM, renderizações e custo de eventos |
| Instabilidade visual | CLS, dimensões de mídia e troca de fontes/layout |
| API/banco | Latência e percentis, queries por requisição, plano de execução, índices, payload e paginação |
| Memória | Heap/retained references, listeners, caches sem limite e GC |
| Jogo | Frame time no dispositivo alvo e pior cena representativa; lógica/input/áudio preservados |
| GPU/inferência | Métricas e profiler da stack escolhida, apenas no escopo autorizado e com admissão atual |

Lighthouse/DevTools oferecem condições controladas. Dados de uso real, quando já disponíveis, ajudam a validar impacto para usuários; não instalar telemetria ou enviar dados automaticamente. Sem RUM, limitar a conclusão ao cenário medido.

Budgets de bundle, latência ou FPS vêm do projeto e do objetivo. Valores de exemplos não são SLAs universais. Confira documentação atual para limites de Core Web Vitals antes de recomendar metas.

Corrija o maior gargalo demonstrado. Refaça medição e verifique correção funcional, acessibilidade, segurança e fidelidade. Depois dos checks necessários, não repetir benchmarks sem mudança ou dúvida concreta. Métricas e critérios de aceite do projeto prevalecem.
