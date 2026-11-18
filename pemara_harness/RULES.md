# Pemara Harness Rules

1. O ledger SQLite e o event log são a fonte de verdade da tarefa durável.
2. Nunca repetir automaticamente um efeito externo cujo resultado seja incerto.
3. Persistir um checkpoint novo antes de cada efeito externo material.
4. Usar uma chave de idempotência estável por tarefa e intenção de efeito.
5. O modelo pode pedir conclusão, mas não pode aprovar a própria conclusão.
6. Continuidade não significa loop infinito: toda tarefa tem orçamento de rodadas.
7. Lease vencido pode ser recuperado; lease vivo nunca pode ser roubado.
8. Não armazenar credenciais, prompts privados ou dados clínicos no repositório.
9. Manter o DeepSeek Harness e a Reversa como upstreams limpos e fixados por commit.
10. Não alterar nem interromper OpenCode, Qwen, ComfyUI ou outros serviços para desenvolver este projeto.
11. Implementar comportamento novo por teste primeiro e registrar correções no `FIXLOG.md`.
12. Qualquer exposição online futura exige revisão pelo guardião de segurança Pemara.
