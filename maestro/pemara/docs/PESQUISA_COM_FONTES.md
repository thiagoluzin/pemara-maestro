# Pesquisa com fontes no Maestro

Integrado em 02/11/2026. Abra o Maestro e selecione **Pesquisa com fontes**. O painel usa o fluxo público existente do `pemara_harness`: coleta pelo Firecrawl MCP, verificação estruturada pelo TypeSafe e preservação das evidências. O PEMARA EDU permanece fora desta etapa, por último na ordem de integração.

## Uso

1. Informe o assunto e, opcionalmente, selecione um projeto existente. O vínculo fica no registro da pesquisa; não modifica o projeto ou suas referências canônicas.
2. Para personagem existente, escolha esse tipo e informe obra, edição/época e encarnação/traje. Isso evita misturar versões na pesquisa.
3. Informe os domínios públicos permitidos e URLs HTTPS ou uma consulta. Cada domínio precisa corresponder exatamente ao host das fontes; inclua os subdomínios necessários. Confirme que todo o texto enviado é público.
4. Informe as afirmações a conferir, uma por linha, e envie. Aguarde o dossiê; ele continua disponível no histórico após recarregar a página.
5. Leia as fontes preservadas, compare as afirmações e registre a revisão. Somente afirmações sustentadas podem ser aceitas; as demais exigem exclusão ou pedido de novas fontes. A revisão não aprova mídia, identidade visual, montagem ou publicação.

O painel permite baixar o dossiê e ler o conteúdo coletado como texto. Cada fonte mostra URL, data da coleta, hash SHA-256, indicação de cache e elegibilidade para verificação. Conteúdo de cache pode estar desatualizado; afirmação sustentada por uma fonte não equivale a uma verdade independentemente confirmada.

## Limites e chamadas externas

- Até três fontes, doze afirmações e oito domínios por pesquisa; uma pesquisa ativa por vez.
- Um lote TypeSafe por pesquisa, com limiar inicial de 0,9. O limiar é operacional e não uma calibração estatística de acerto.
- Texto acima de 26 mil caracteres por fonte é preservado, mas não enviado à verificação; o estado combinado enviado também é limitado a 48 mil caracteres.
- Apenas conteúdo público: o assunto, a consulta, as afirmações e o texto coletado podem chegar aos provedores do fluxo. Não enviar documentos privados, dados escolares ou credenciais.
- Créditos Firecrawl e tokens TypeSafe ficam no dossiê quando informados pelo provedor. O painel não calcula preço monetário nem garante tarifa gratuita.
- Repetir o mesmo envio com o mesmo identificador reaproveita o registro. O botão de nova pesquisa cria outra intenção. Falha/interrupção não dispara replay automático de chamadas externas.

## API e persistência

O navegador acessa `/api/studio/api/research`; no Studio, o prefixo é `/api/research`. Todas as rotas exigem o contexto interno autenticado do Maestro, inclusive leitura de fontes e download.

| Método | Rota relativa | Função |
| --- | --- | --- |
| GET | `/jobs` | Histórico paginado |
| POST | `/jobs` | Envio idempotente, resposta 202 |
| GET | `/jobs/{id}` | Estado, fontes, afirmações e revisão |
| POST | `/jobs/{id}/reviews` | Revisão factual persistente |
| GET | `/jobs/{id}/sources/S1` | Fonte preservada em texto puro |
| GET | `/jobs/{id}/dossier` | Download do dossiê |

Os dados ficam em `dados/studio/public_research/{id}/`: pedido, especificação, registro, logs do processo, revisões e a pasta `run/` produzida pelo Harness. Ela preserva o dossiê, fontes, recibos, manifesto e ledger SQLite. O manifesto é conferido na leitura do detalhe; alteração de evidência bloqueia a revisão e os downloads daquele resultado. O histórico resumido evita reprocessar todos os arquivos antigos.

O servidor rejeita campos extras, URLs fora dos domínios, corpos acima de 32 KB e tipos de conteúdo diferentes de JSON. Fontes são tratadas como dados não confiáveis, exibidas por `textContent` ou texto puro, sem execução de HTML. O cliente não fornece credenciais de provedor nem sinal de aprovação.

## Operação

O bridge usa o Node instalado em `C:/Program Files/nodejs/node.exe` e o Harness em `E:/Pemara/pemara_harness`. O comando é fixo, sem shell; os parâmetros públicos ficam em JSON. Credenciais continuam nos mecanismos existentes do Harness e no ambiente do processo, sem cópia para a interface. Timeout de oito minutos afeta apenas o filho iniciado pela pesquisa. Após reinício, o serviço reconcilia artefatos concluídos e sinaliza interrupções sem relançá-las.

O Studio foi atualizado pelo Radar, preservando o ComfyUI e o histórico de geração. O helper `restart_studio.ps1` agora identifica o dono real da porta mesmo quando o Windows omite o estado do socket, e só confirma saúde quando o novo processo é o dono da porta. O falso positivo anterior de reinício não basta para declarar implantação.

## Validação de 02/11/2026

Onze testes de API/serviço e um teste de navegador passaram. A interface foi verificada em 1440, 390 e 320 pixels, incluindo leitura segura, revisão, idempotência, vínculo sem modificar projeto e ausência de overflow horizontal. O teste de navegador foi repetido após os ajustes finais de layout.

Um piloto real enviado pela sessão autenticada do Maestro terminou em `READY_FOR_REVIEW`: uma fonte pública, duas afirmações, uma sustentada e outra sem sustentação/incerta. Consumo informado: um crédito Firecrawl, um lote TypeSafe, 1810 tokens de entrada e 79 de saída. O piloto permanece aguardando revisão do proprietário.

Evidências: `dados/validation/maestro_research_20261102/`. O recibo de segurança cobre este componente e seus controles de integração; não é uma auditoria completa de toda a plataforma. Nenhuma geração de mídia, alteração de aprovação artística ou integração no PEMARA EDU foi feita.
