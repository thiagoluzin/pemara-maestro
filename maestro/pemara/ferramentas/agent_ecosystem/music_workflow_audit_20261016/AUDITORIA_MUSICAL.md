# Auditoria da geração musical do Maestro — 16/10/2026

## Resultado e ativação

O código foi corrigido para YuE2 como padrão de novas músicas. A interface preserva uma escolha explícita de outro motor e não troca automaticamente para ACE-Step quando YuE2 está indisponível. A preferência musical tem campo próprio, separado de SFX, com compatibilidade para o backend anterior.

**A ativação completa do backend está pendente de reinício administrativo.** O processo em execução ainda anuncia `audio_provider=levo2_local`, não publica `music_provider` nem a capacidade de geração direta. YuE2 está configurado. A sessão disponível do navegador pede login, por isso a seleção em uma sessão autenticada não foi conferida.

O reinício oficial pelo Radar falhou com “Acesso negado” ao parar o Studio. A revisão automática bloqueou a tentativa de relançar o supervisor pela tarefa administrativa existente (“blocked by policy”); essa ação não foi executada. A solicitação própria de reinício foi arquivada, retirando a repetição indefinida. Serviços e trabalhos existentes permanecem em execução.

Para ativar depois de confirmar fila/reserva livres, executar o [reiniciador oficial do Studio](E:/Pemara/maestro/pemara/services/studio/restart_studio.ps1) em uma sessão administrativa e atualizar o Maestro. Não é necessário recriar músicas. Conferir então `defaults.music_provider=yue2_local` e `providers.audio.yue2_local.supports_direct_generation=true`.

## Problemas encontrados e correções

| Prioridade | Problema e efeito | Entrega |
|---|---|---|
| Alta | O backend preferia LeVo/Lyria, contrariando YuE2 como padrão. A UI preservava valores automáticos do select e podia manter ACE-Step, primeiro provedor da lista. | Padrão YuE2 no backend e HTML; memória por modalidade apenas para escolhas explícitas; sem substituição por disponibilidade. |
| Alta | Não havia opção de geração direta no Maestro; o automático sempre compunha ABC. Isso impedia reproduzir o método direto usado na direção sonora preferida pelo proprietário neste lote. | Modo direto opcional, mantendo Qwen 3.8, checkpoint YuE2, fonte, evidência de fim e duas tentativas limitadas. Partitura manual e automático com partitura continuam disponíveis. |
| Média | Direção sonora e descrição técnica de produção eram mescladas no mesmo caption. | Caption sonoro separado para o modo direto; plano completo continua preservado como metadata. |
| Média | A instrução para músicas longas reduzia a forma a dois versos e refrão, favorecendo letras curtas e estruturas repetidas. | Qwen orientado a desenvolver narrativa, hooks e contrastes conforme andamento/duração. É uma correção de direção textual; ainda exige qualificação por escuta. |
| Alta | Duração escolhida pelo Qwen podia perder a identificação de escolha automática no resultado. | Proveniência conserva a escolha e identifica a origem; o tempo escolhido pelo Qwen não vira teto nativo de quinze minutos na rota direta. |
| Média | Os especialistas musicais existiam, mas o fluxo obrigatório e a responsabilidade específica por composição/letra não estavam claros. | Novo compositor/letrista, cinco responsabilidades encadeadas e registro canônico obrigatório no AGENTS e Messenger. |

A geração direta é uma alternativa, não uma declaração de superioridade em todos os gêneros. Não tornei o CFG 1.6 do lote metal um padrão universal. O novo modo usa o comportamento nativo compatível com o runtime; a UI só o habilita quando o backend anuncia suporte, evitando incompatibilidade durante a atualização.

## Agentes e skills obrigatórias por fase

1. **Direção:** `pemara-music-production-lead` fixa intenção, referências musicais, motor, idioma, instrumentos e duração.
2. **Composição/letra:** `pemara-music-songwriter` usa Qwen 3.8 para história, hook, cantabilidade e forma.
3. **Arranjo:** `pemara-music-arranger` define decisões de riff, baixo, bateria, interpretação, contraste e solo.
4. **Mix/entrega:** `pemara-music-mix-engineer` preserva fonte e verifica WAV/MP3 efetivos.
5. **Escuta:** `pemara-music-listening-qc` separa evidência técnica, direção aprovada e aprovação da faixa exata.

São papéis que um agente pode assumir sequencialmente; não foram criados processos, chats ou subagentes permanentes. A presença das skills não comprova que houve escuta nem que o backend executa instruções Markdown. O AGENTS e o roteador exigem seu uso pelo agente na fase correspondente.

Fluxo canônico: [creation-workflow.md](E:/Pemara/.agents/skills/pemara-music-production-lead/references/creation-workflow.md). Novo especialista: [pemara-music-songwriter](E:/Pemara/.agents/skills/pemara-music-songwriter/SKILL.md).

O contrato também foi corrigido para distinguir criação nativa em mix do YuE2 de reinstrumentação por stems/MIDI: texto descrevendo ganhos não demonstra que pistas independentes foram processadas.

## Próximas melhorias recomendadas no Maestro

| Ordem | Melhoria | Critério de aceitação |
|---|---|---|
| 1 | Duração como intervalo mínimo/máximo, persistido no pedido e aplicado ao áudio final. Hoje o teto nativo não garante o mínimo. | Uma faixa de 3:56 nunca aparece como concluída em um pedido de 4–6 minutos; sem silêncio, corte ou alteração de velocidade para passar. |
| 2 | Registro persistente de todas as tentativas, inclusive falhas, e retomada de lotes por faixa. | Após queda ou erro, retomar só pendentes, mantendo IDs, arquivos, hashes, crítica e candidato ativo. |
| 3 | Perfis sonoros configuráveis por gênero e intensidade, com A/B autorizado. | Comparação em volume equivalente e escuta de um piloto antes de multiplicar método incerto; métricas não aprovam peso ou criatividade. |
| 4 | Idioma e referências como campos explícitos do brief, preservados até a revisão vocal. | O pedido em inglês não pode ser silenciosamente reescrito para outro idioma; texto e canto são verificados separadamente. |
| 5 | Resolver o MERT por configuração/cache válido e expor a dependência ausente. | Readiness coerente com arquivos reais e teste offline; nenhuma instalação/download implícito. |
| 6 | Consolidar o painel legado de áudio com o criador principal. | Um único seletor mantido, evitando markup antigo que ainda lista Lyria por padrão e não tem handler correspondente em assets JS. |
| 7 | Corrigir a identidade/permissão do supervisor de manutenção. | Reinício administrativo funciona sem retries indefinidos, com pré-verificação de trabalhos/reservas e recibo de versão ativa. |

O MERT usado pela reinstrumentação é procurado por um caminho absoluto no cache C:. O status informou `needs=[mertModel]`; os três caches pertinentes conferidos não apresentaram seus pesos. Isso afeta a prontidão dessa rota, não autoriza aprovar música por embeddings nem substituir a escuta.

## Verificações realizadas

- 57 testes focados de criação, duração, geração direta, preservação de letras/BPM e revisão: passaram.
- 6 cenários comportamentais JavaScript: padrão YuE2 com servidor novo/antigo, escolha explícita, indisponibilidade, separação de SFX e provedor ausente: passaram.
- Suíte musical completa final: **136 testes; 134 passaram e 2 falharam**. Falhas em `test_music_ai_api` e `test_music_reinstrument` pela dependência MERT não pronta. Não foram mascaradas nem foi instalado modelo.
- Grafo direto exato validado pelo MCP no runtime ativo: válido, zero erros/avisos, sem nós pagos. Não foi enviado para geração.
- Sintaxe Python e JavaScript: válida.
- Novo especialista e skill principal validados; inventário musical e registro de 42 aliases/8 especializações sem erros.
- Backup dos arquivos anteriores, comparação por hash e patch do escopo preservados nesta pasta.

Testes não provam melhora artística do novo prompt ou modo. A qualificação criativa futura precisa de áudio autorizado e escuta do candidato exato. Nenhuma música foi gerada, reprocessada, apagada ou publicada nesta auditoria.

## Referências consultadas

- [YuE2 — modelo e modos oficiais](https://huggingface.co/m-a-p/YuE2-3B).
- Implementação instalada `D:/PemaraRuntimes/ComfyUI-v0.40.0-pemara/comfy_extras/nodes_yue2.py`: ABC vazio ativa modo `off`.
- [TypeSafe — índice vivo](https://docs.typesafe.ai/llms.txt), skill obrigatória e regras determinísticas preservadas, sem nova API paga.

