# Consolidação implementada — 2026-10-08

Implementação autorizada de [RECOMENDACOES.md](../optimization_audit_20261008/RECOMENDACOES.md). Roteamento, famílias, referências, metadados e conflitos de vídeo foram tratados. Nenhum vídeo foi gerado; nenhum serviço reiniciado.

## Resultado

- Messenger como roteador único; Ecosystem como manutenção; dispatcher como compatibilidade.
- 41 aliases e oito especializações preservadas. Inclui as quatro funções de música acrescentadas durante o trabalho; cinco antigos perfis duplicados viraram aliases.
- Planejamento, depuração, performance e frontend vanilla têm uma entrada canônica por família e módulos por necessidade. Testes, segurança, áudio, motores de jogos e departamentos de vídeo continuam distintos.
- As 54 skills do núcleo curado passaram no validador e têm `agents/openai.yaml`; 33 lacunas do núcleo e quatro wrappers receberam metadados novos.
- Cinco entradas longas foram reduzidas, movendo receitas para referências acessíveis. O relatório `verification.json` contém bytes antes/depois; isso não mede tokens, latência ou custo.
- Acabamento do pacote live action corrigido para SeedVR2 3B int8 → RIFE exato 60 → DLSS5 Natural → áudio existente, com picture lock e revisão separados. Não há RealESRGAN ou Foley novo nesse plano.
- Combate distingue defesa ativa e reação involuntária ao impacto; showrunner diferencia gesto isolado de luta bilateral contínua, geometria e função das âncoras. A aprovação exata e as identidades originais seguem obrigatórias.
- Mapas atuais apontam para contratos vigentes; mapa anterior preservado como histórico.
- Onze instalações duplicadas têm `enabled=false` por caminho em `config.toml`. Arquivos originais permanecem disponíveis; backup integral privado verificado por hash e CRC.

## Ativação da descoberta

**Reinicie o Codex quando for conveniente para aplicar a desativação das duplicatas.** A documentação oficial exige reinício após alterar `config.toml`: [Enable or disable local Codex skills](https://learn.chatgpt.com/docs/build-skills#enable-or-disable-local-codex-skills). O aplicativo não foi reiniciado nesta tarefa e a descoberta após reinício ainda não foi observada. Os arquivos e overrides já estão gravados.

HyperFrames canônico: `C:/Users/admin_remoto/.agents/skills`, instalação gerenciada de `heygen-com/hyperframes` atualizada em 2026-10-07. As cópias antigas em `.codex/skills` foram preservadas. O comparativo considera regras de execução de plugins, layout de referências e compatibilidade; não apenas tamanho/data. A entrada foi delimitada à stack HyperFrames, com modo somente plano explícito. Caches de plugins não foram editados.

## Evidências

- [Verificação estruturada](verification.json): registro, 54 skills, metadados, links, hashes e tamanho das cinco entradas.
- [Requisitos e oito cenários](REQUISITOS_E_CENARIOS.md): destino de cada responsabilidade e limites da avaliação.
- [Revisão independente final](REVISAO_INDEPENDENTE_FINAL.md): releitura e decisões observadas.
- [Recibo de alterações](changes.json): hashes antes/depois e backup por arquivo.
- [Descoberta e backup privado](discovery_receipt.json): onze caminhos desativados, comparação e hash de cada membro do ZIP.
- [Trabalho concorrente preservado](concurrent_preserved.json): apêndice musical e registro revistos sem sobrescrever a contribuição.

Validação de código: `python -B -m unittest test_live_action_workflows`, em `maestro/pemara/services/studio`: **20 testes passaram**, incluindo o plano compilado de acabamento corrigido. Os testes materializam/validam contratos locais, sem enviar geração. Avisos existentes de pynvml/audioop não impediram a suíte; dependências não foram alteradas.

Não foi produzido filme para avaliar realismo. A preservação foi verificada por requisitos, referências, exercícios de encaminhamento e testes dos contratos afetados; qualidade artística continua dependendo da revisão da mídia real e da aprovação do proprietário. Pacotes externos não foram todos auditados; referências Unity ausentes estão documentadas no mapa de cenários.

## Reversão segura

Não executar os scripts `phase*.py` novamente: são registros reproduzíveis da aplicação inicial, com guardas de concorrência, não instaladores idempotentes.

Para reverter, consultar `changes.json`, conferir que cada arquivo ainda coincide com `after_sha256` e que o backup corresponde a `before_sha256`. Se houver diferença, revisar e mesclar; nunca restaurar por cima de trabalho posterior. Restaurar somente os arquivos desejados, mantendo snapshot da versão atual. Arquivos novos têm `backup: null`; preservá-los fora da descoberta antes de retirar seus vínculos.

Para as duplicatas, remover somente os onze blocos `[[skills.config]]` listados no recibo, depois de conferir que continuam com os mesmos caminhos/valores. Não substituir o config inteiro se outras preferências mudaram. A cópia anterior do config fica **somente** em `C:/Users/admin_remoto/.codex/backups/skill_consolidation_20261008/config.toml.before`, fora do repositório. Não imprimir seu conteúdo. Os pacotes antigos não precisam ser reinstalados.

O arquivo `duplicate_skill_sources.zip` no mesmo diretório privado preserva integralmente as cópias desativadas. O histórico de mídias, modelos, projetos encerrados e aprovações não foi modificado.
