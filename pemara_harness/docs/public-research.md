# Pesquisa pública com fontes no Pemara Harness

Fluxo disponível por comandos do próprio Harness e pela exportação `@pemara/harness/research`. Não exige iniciar Qwen, ComfyUI ou alterar o motor das conversas. A interface de chat e seus perfis ativos permanecem os existentes; esta entrega não adiciona um botão ao cockpit nem dispara pesquisas automaticamente ao conversar.

O operador fornece uma especificação pública. O Harness pesquisa/coleta pelo Firecrawl MCP, preserva as fontes e verifica afirmações com Gemini Decision. Salva um dossiê e uma fila de revisão, mantendo a conclusão pendente de verificação independente no ledger SQLite.

## Usar

```powershell
Set-Location E:\Pemara\pemara_harness

# Validar escopo e orçamento sem rede:
npm.cmd run research:plan -- --spec docs/research-pilot.json

# Usar uma pasta nova para cada tentativa explicitamente autorizada:
npm.cmd run research -- --spec docs/research-pilot.json --output .runtime/research/minha-pesquisa-01

# Conferir o estado e os hashes dos arquivos preservados:
npm.cmd run research:status -- --output .runtime/research/minha-pesquisa-01
```

O piloto executado neste trabalho está em `.runtime/research/public-pilot-20261102`. Não repetir o piloto para conferir o resultado: usar `research:status` e abrir seus arquivos. Pastas existentes são recusadas antes de qualquer nova chamada externa.

## Especificação

Use `docs/research-pilot.json` como referência. Campos:

- `schemaVersion: 1`, `id` único e `topic` descrevem a pesquisa.
- `publicOnly: true` declara que consulta, afirmações e URLs são públicas e autorizadas para os serviços externos. Não incluir credenciais, dados pessoais, histórico de conversas ou documentos privados.
- `allowedDomains` é a lista exata dos hosts permitidos, sem wildcard. Indica a seleção do operador, não certifica que uma fonte seja oficial ou independente.
- `urls` fornece fontes conhecidas. `query` opcional pesquisa fontes adicionais até `maxSources`.
- `claims` contém até 12 afirmações específicas a verificar. `sourceUrl` limita uma afirmação a uma fonte; `quote` opcional precisa aparecer no texto preservado antes de seguir ao modelo.
- `maxSources` vai de 1 a 3. Há no máximo uma pesquisa, três coletas e um lote Gemini Decision por execução. Os limites são de chamadas lógicas, não um teto monetário garantido.
- `threshold` é um limiar experimental de confiança, padrão 0,9, entre 0,8 e 1. Deve ser validado com casos reais do domínio.
- `model` padrão `gemini-decision-1`; o modelo real retornado fica registrado. Não há troca de motor por falha.

Aceitamos somente HTTPS público, sem usuário, senha, query string ou porta explícita. URLs de resultados fora da allowlist são descartadas antes da coleta. Os serviços remotos resolvem as URLs; esta validação não é uma sandbox de rede nem substitui a classificação correta dos dados pelo operador.

## Fontes e verificação

Preservamos o Markdown e a resposta estruturada original, URL pedida, URL/metadados reportados pelo serviço, data, cache e SHA-256. Datas de coleta/cache não comprovam data de publicação, versão canônica ou atualidade do conteúdo. Resultados de busca são candidatos; a afirmação é julgada contra o conteúdo efetivamente coletado.

Cada fonte elegível entra inteira no contexto de verificação. Acima de 26.000 caracteres, ela fica preservada mas não é enviada ao Gemini Decision. O estado completo tem limite de 48.000 caracteres; fontes adicionais que não cabem recebem motivo explícito. Não há truncamento silencioso. Várias URLs da mesma documentação não equivalem a fontes independentes.

Citações ausentes são detectadas em código, com normalização de espaços e aspas. Para as restantes, um único lote de perguntas `Choice` avalia a relação entre cada afirmação e sua fonte: `supports`, `contradicts` ou `unsupported`. A resposta precisa ter tipo, opção, probabilidades e confiança válidos. Uma coincidência textual não basta para marcar sustentação contextual.

Todo conteúdo externo permanece dado não confiável, sem execução de instruções, ferramentas ou scripts vindos da página. O modelo recebe instruções fixas para ignorar comandos embutidos e avaliar apenas o conteúdo. Isso reduz exposição, sem constituir garantia de resistência semântica a todo ataque de prompt.

## Artefatos

- `dossier.md` e `dossier.json`: fontes, hashes, afirmações, julgamentos, consumo e limites.
- `review-queue.json`: afirmações contraditas, incertas, sem evidência ou com problemas de resposta.
- `sources/S*.md` e `S*.raw.json`: fontes exatas preservadas.
- `search.json`, `verification-request.json` e `verification-response.json`: recibos das chamadas efetivamente feitas; os arquivos de verificação não existem quando o lote é desnecessário.
- `manifest.json`: hashes dos artefatos de evidência. `research-status` sinaliza alterações, com saída diferente de zero quando a integridade não está confirmada.
- `research.sqlite`: tarefa e efeitos no ledger nativo do Harness, independente das tarefas de produção.

Os arquivos ficam em `.runtime`, fora do Git. `manifest.json` detecta alterações acidentais; alguém capaz de substituir também o manifesto pode fabricar novos hashes. Para revisão consequente, preserve um hash de confiança em separado.

## Revisão e falha

`SUPPORTED` indica sustentação contextual nas fontes daquele lote. Não prova verdade universal, aprovação do proprietário ou qualidade artística. O dossiê sempre tem `approved: false` e `humanReviewRequired: true`; a tarefa termina em `COMPLETED_PENDING_VERIFY`.

Falha ambígua não é repetida: o efeito permanece `STARTED`, os arquivos já recebidos são preservados e `status.json` indica `INTERRUPTED_REVIEW_REQUIRED`. Quando possível, há `dossier.partial.md`. O operador pode usar os comandos existentes de recuperação/resolução do ledger, apontando `--db <pasta>/research.sqlite`. Não marcar um efeito como concluído sem conferir o recibo real. Este comando não implementa retomada automática; nova tentativa exige pasta nova e reconciliação do efeito anterior quando necessário.

O adaptador REST Gemini Decision usa o endpoint oficial fixo, timeout de 60 segundos e uma única tentativa. A chave vem de GEMINI_API_KEY/GOOGLE_API_KEY ou do arquivo privado gemini.env, sem persistência em recibos. Falhas não trocam de provedor.

## Validação e dependências

Testes offline em `test/research.test.mjs` e `test/research-providers.test.mjs`; piloto real público documentado nos recibos. Os testes normais não chamam serviços externos. Dependências fixadas: `@modelcontextprotocol/sdk@1.32.2` e `REST Gemini Decisions v1beta`, com lockfile; reinstalação por `npm.cmd ci --ignore-scripts`.

O contrato fixo anterior fica preservado. A inclusão legítima de novos testes/configuração exige um novo contrato de avaliação, conforme `docs/fixed-evaluation.md`.

Fontes vigentes consultadas em 2026-11-13: [Gemini Decisions API](https://blog.google/innovation-and-ai/technology/developers-tools/gemini-decisions-api/), [contrato e tipos oficiais](https://github.com/googleapis/python-genai/tree/main/google/genai/_gaos/types/decisions) e [Firecrawl MCP](https://github.com/firecrawl/firecrawl-mcp-server). Recibos anteriores permanecem históricos. O piloto não certifica confiabilidade geral.
