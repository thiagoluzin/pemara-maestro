# Política de DLSS 5 por tipo de produção — 2026-10-09

Implementada a instrução do proprietário: DLSS 5 proibido nos atores em live action; permitido no quadro inteiro em animação.

| Tipo declarado | Comportamento |
| --- | --- |
| Live action | DLSS aplicado ao cenário; atores completos restaurados da fonte imediatamente anterior ao DLSS por máscara revisada. |
| Mista | Mesma proteção dos atores live action. |
| Animação | DLSS integral permitido. |
| Indefinido ou conflitante | Bloqueio antes da exportação tratada; selecionar o tipo. |

O Maestro recebeu seleção de tipo na criação e na edição de projetos. A declaração é persistida e acompanha a geração e o upscale. Os builders especializados de live action incluem a política explicitamente. As prévias nativas de live action podem ser salvas sem DLSS, com recibo pendente de máscaras; elas não qualificam como acabamento final.

O processamento final de vídeo requer contrato de proteção com máscaras revisadas por quadro, vinculado aos bytes, dimensões e cadência da fonte imediatamente anterior ao DLSS. Esta alteração não adiciona rastreamento automático nem classificação visual automática.

Foram atualizados o backend, exportadores ComfyUI, perfis, template de âncora, instruções AGENTS e quatro skills de produção com referência compartilhada. O carregador PNG/WebP preserva os valores da máscara sem a quantização observada no carregador anterior.

Validação: 170 testes aprovados; quatro skills validadas; sintaxe JavaScript aprovada; criação e alteração do tipo de projeto verificadas. Os novos nós foram carregados no ComfyUI ativo e executados em três verificações técnicas. A máscara real passou pelo novo carregador sem alterar nenhum valor de canal. Não houve nova geração criativa.

Os hashes do vídeo V15 e da âncora de Jill aprovada permaneceram iguais. Backups individuais, hashes anteriores e posteriores constam de BACKUP_MANIFEST.json e CHANGES.json; evidências constam de VERIFICACAO.json.

Os componentes ComfyUI foram recarregados. O backend Maestro não estava em execução; suas alterações e as da interface serão carregadas na próxima inicialização. A interface não foi validada visualmente nesta sessão. O log retornado pelo MCP era antigo; a validação atual foi feita pela execução dos nós e consulta da fila ativa.
