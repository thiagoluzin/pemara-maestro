# Da crítica à correção

Priorize a falha que torna a cena ilegível ou falsa. Identidade, causa física e incompatibilidade de rota são bloqueios independentes; não escondê-los com nota média. Depois trate performance/fotografia/ritmo. Integridade técnica continua obrigatória.

| Sintoma visto/escutado | Investigar na fonte | Correção executável |
|---|---|---|
| Ator robótico ou sem reação | objetivo, estímulo, olhar e excesso de gestos | um gesto dominante; resposta motivada e recuperação |
| Luta genérica | golpe assinatura, iniciativa, defesa e consequência | trave mecânica por personagem e leitura do contato |
| Impacto parece leve | apoio, centro de massa, causa/reação | mostre impulso, contato, deslocamento e perda/recuperação de base |
| Câmera parece aleatória | geografia, informação revelada e saída | trajetória única motivada, eixo claro e handoff compatível |
| Tudo tem aparência plástica | referência, material, luz e contraste | corrigir âncora/rota visual; não tentar salvar com sharpening |
| Rosto/roupa varia | ficha original, condição e anchors | restaurar identidade fixa e estado por take sem apagar danos |
| Corte salta ou reinicia | Estados nas saídas e entradas reais, velocidade, fase e geografia | Corte direto se compatíveis. Estados diferentes com caminho causal exigem Flow. Se identidade ou geografia impedirem o caminho, corrija a fonte. |
| Vídeo longo e vazio | mudança real por beat e duração útil | reduzir repetição ou redesenhar a progressão dentro do contrato |
| Filme confuso mesmo com takes bons | causa, ponto de vista e cobertura | reorganizar fontes aprovadas ou devolver lacuna à direção |
| Som não tem peso | evento visual, timing, perspectiva e mix | corrigir somente áudio autorizado; ouvir a candidata inteira |

## Iteração controlada

1. Registre a crítica do proprietário e o arquivo afetado, sem reinterpretar como aprovação parcial inexistente.
2. Separe observação de hipótese. Exemplo: 'defensor começa a voar antes do contato' é observação; 'guia final está puxando a pose' é hipótese.
3. Preserve aspectos aprovados e faça uma mudança principal de método por tentativa quando viável. Não variar ao mesmo tempo rosto, câmera, golpe, luz e motor.
4. Gere nova tentativa do mesmo escopo quando a crítica autorizar, houver admissão GPU e grafo validado pelo MCP. Pedido de pausa/sem gerar prevalece. Uma falha detectada só pelo agente não amplia autorização nem reabre projeto finalizado.
5. Após duas falhas equivalentes, revise densidade de eventos, staging ou estratégia de controles, mantendo o motor. Não girar seeds indefinidamente. Âncoras extras não são solução universal: em combate contínuo, controles futuros podem antecipar a reação.
6. Compare a substituta com o rejeitado e com a ficha original no defeito e nos aspectos preservados. Mostrar evidência do novo arquivo; não anunciar que resolveu antes de observar.
7. Mantenha rejeitado fora de âncoras/montagem e nova candidata pendente da avaliação do proprietário. Não promover com base em relatório técnico.

Para falha sistêmica, preserve a rota como rollback e prepare uma rota coerente dentro do mesmo escopo. Não iniciar lote extenso até uma tentativa representativa demonstrar que o método mudou o defeito.

## Registro verificável de reparo — 2026-10-09

Em sequências live action, registrar `attempts` por take no contrato de câmera com status, falha, método, arquivo/hash e observação. Duas falhas equivalentes bloqueiam repetir o método: nome novo ou seed diferente não são mudança de estratégia. Conferir o piloto montado antes do restante do lote. Para aparência de cera, compare a fonte com a âncora após o DLSS, depois o take nativo com o vídeo após Lanczos/RIFE. Assim é possível localizar a primeira mudança. SeedVR2 em live action aparece apenas na investigação histórica. Consulte o [contrato de câmera](camera-evidence-and-actor-protection.md) e o [contrato de âncoras e acabamento de vídeo](dlss5-full-frame-required.md).
