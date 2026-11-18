# Criação musical obrigatória no Maestro

Aplicar a novas composições e correções musicais, conforme o [contrato de produção](music-production-contract.md). A função de reinstrumentação foi removida do Maestro em 2026-10-16 por ordem do proprietário. Auditoria, escrita de skills e mudança de padrão não autorizam gerar mídia nem reinstalar o sistema removido.

## Responsáveis e entregas

| Fase | Skill obrigatória | Evidência que entrega |
|---|---|---|
| Direção | `pemara-music-production-lead` | Brief: motor, idioma, instrumentos, intenção, limites de duração e referências em termos musicais |
| Composição e letra | `pemara-music-songwriter` | Letra original, narrativa, hook, prosódia e forma propostos pelo Qwen 3.8, com escolhas do proprietário preservadas |
| Arranjo | `pemara-music-arranger` | Contrastes de riff/groove/voz/solo, papéis por instrumento e modo YuE2 escolhido com motivo |
| Mix e entrega | `pemara-music-mix-engineer` | Fonte preservada, WAV/MP3 reais, decode, clipping, true peak e hashes |
| Revisão | `pemara-music-listening-qc` | Parecer com timestamps ou pendência explícita de escuta; retorno exato do proprietário |

São responsabilidades sequenciais; um agente pode assumir todas. Não criar cinco chats/processos por causa desta tabela. Presença em disco, plano JSON ou passagem em teste não comprovam execução criativa dos papéis.

## Agente de gênero e especialistas complementares

Escolha `pemara-heavy-metal`, `pemara-thrash-metal`, `pemara-punk-rock` ou `pemara-death-metal` quando esse for o gênero solicitado. As configurações de agente apontam para as skills canônicas; não duplicar regras musicais nos perfis. Outros gêneros continuam no fluxo geral.

Em canções, `pemara-music-vocal-director` dirige prosódia e interpretação antes da geração e revisa a emissão no áudio. Em lotes, `pemara-music-album-diversity` compara hooks, motivos, grooves, forma e fraseado antes e depois da geração. Veja [quality-evidence.md](quality-evidence.md) para entregas, limites da triagem e tratamento de falhas. Configurar agentes não os inicia nem autoriza GPU.

## Escolha do método

- YuE2 é o padrão, mantendo outros motores como escolhas explícitas. Não substituir o escolhido por disponibilidade.
- Partitura é útil para controle de notas/estrutura; geração direta sem ABC é uma alternativa para criação livre. Compare candidatos quando autorizado; não afirmar que um modo é superior para todos os gêneros.
- Preserve letra fornecida, idioma, instrumental, BPM explícito e faixa de duração. Se houver mínimo e máximo, medir ambos no áudio efetivo. O teto nativo não garante duração mínima nem canto completo.
- O plano Qwen informa intenção. Ganhos, densidade, BPM e instrumentos escritos no prompt não equivalem a stems reais nem à medição do áudio.
- Parâmetros de uma tentativa metal aprovada como direção não viram padrão universal. Registrar checkpoint, modo efetivo, CFG semântico/acústico, seed e origem da avaliação.

## Lotes e correções

Para um lote com direção ainda rejeitada/incerta, produzir e avaliar um piloto representativo antes de multiplicar o método. A aprovação da direção permite prosseguir dentro do pedido, mas não aprova automaticamente cada faixa. Não interromper um lote já autorizado para pedir a mesma aprovação outra vez.

Se uma faixa terminar curta, não preencher com silêncio, repetir o arquivo, acelerar/desacelerar ou cortar para passar. Reavaliar densidade da letra, forma e desenvolvimento instrumental. Repetir o refrão pode ser uma escolha artística, mas não é reparo automático de duração. Após duas falhas equivalentes, mudar a hipótese/método e registrar por quê; limitar tentativas conforme orçamento autorizado, preservando arquivos e IDs.

Não usar supressão isolada do fim da geração para atingir minutos: ela pode prolongar ruído/quase silêncio. Conferir sinal por intervalos e final musical real. O lote rejeitado/apagado em 2026-11-10 não pode ser retomado para experimentar estas regras sem um novo pedido de produção.

Na crítica, registrar candidato/hash → trecho/defeito → decisão de correção. Rejeitado não alimenta nova fonte. Retomar somente itens pendentes após falha, sem duplicar os concluídos.

## Conclusão e publicação

Contar como entregue apenas o arquivo efetivo que passou pelos requisitos técnicos do pedido. Separar `technical_pass`, `direction_approved` e aprovação artística do artefato exato. Escuta indisponível permanece pendente, sem inventar timestamps ou aprovação por MuQ/MERT.

Publicar exige autorização própria. Se solicitado, conferir inventário exato, nome do artista, IDs, ordem da playlist e visibilidade. Limite diário é bloqueio externo: preservar pendências, informar o total efetivamente publicado e não criar automação sem pedido de acompanhamento/agendamento.
