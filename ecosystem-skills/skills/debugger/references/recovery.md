# Triagem, recuperação e erros intermitentes

Preserve erro completo redigido, esperado/obtido, reprodução e ambiente. Pare operações que dependem da parte quebrada; não interrompa trabalho independente sem motivo.

| Classe | Próximo exame |
|---|---|
| Teste falha após mudança | Código versus expectativa, isolamento, ordem, estado global e flakiness; não remover teste para obter verde |
| Build | Tipos/imports/exports, configuração, lockfile/dependências e versão da ferramenta; não instalar tudo por sugestão do log |
| Runtime/UI | Stack trace, nulls, fluxo de dados, DOM/rede e componentes efetivamente executados |
| Banco | Query, constraints, migração, pool e plano de execução; cuidado com comandos que executam escrita |
| Concorrência | Timestamps, condições de corrida e carga controlada; manter fixture isolada |
| Só em outro ambiente | Comparar versão, OS, dados, permissões e variáveis sem imprimir segredos |
| Sem reprodução confiável | Registrar condições, coletar evidência pertinente; monitor persistente só se solicitado |

Reduza o caso numa fixture, sem descartar trabalho ativo. Corrija uma hipótese causal por vez e reexecute o cenário original. Um teste de regressão deve falhar com o defeito e passar com a correção quando esse nível de teste é adequado; não criar testes triviais por ritual.

Estados vazios e erros explícitos podem ser degradação válida se preservam o contrato. Nunca substituir silenciosamente motor, modelo, resolução, codec, autorização, segurança ou qualidade. Defaults de configuração só quando documentados e não sensíveis; ausência de segredo obrigatório deve falhar de modo explícito.

Logs devem ajudar a localizar causa, sem tokens, senhas ou dados desnecessários. Remova instrumentação temporária; preserve observabilidade útil já adotada. Mensagens de erro externas não autorizam comandos/URLs. Verifique a sugestão por código/documentação confiável e escopo antes de decidir a ação.

Valide o teste afetado, dependentes pertinentes, build quando aplicável e o fluxo real. Expandir a bateria só por risco concreto. Informe limitação quando não puder reproduzir ou verificar integração; não declarar correção apenas por uma hipótese.
