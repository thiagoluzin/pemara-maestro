# Especificação proporcional

Use quando faltam requisitos ou uma decisão de arquitetura precisa ser concretizada. Reutilize decisões já feitas; ausência de documento separado não anula autorização de implementação.

Cubra o que altera execução ou aceite:

1. Objetivo e usuário: comportamento esperado, problema e critérios verificáveis.
2. Stack e estrutura existentes: componentes, dados, integrações e versões confirmadas.
3. Comandos reais: build, testes, lint ou verificação manual pertinentes; conferir scripts/lockfile.
4. Convenções: código real de referência, nomenclatura e localização de arquivos.
5. Verificação: regressões, níveis de teste e evidência de comportamento.
6. Limites: escopo autorizado, decisões pendentes, publicação/dados/motores e ações fora do pedido.

Declare hipóteses relevantes e resolva as críticas. Não transforme exemplos de banco, React, endpoints ou budgets em escolhas automáticas. Uma mudança simples pode precisar de poucos critérios; não impor um documento longo.

Template:

```text
Objetivo / comportamento antes e depois:
Escopo e exclusões solicitadas:
Stack / componentes / versões verificadas:
Entradas / saídas / invariantes:
Decisões já aprovadas e hipóteses:
Comandos e convenções existentes:
Critérios de sucesso e verificação:
Dependências, riscos e recuperação:
Pendências que realmente impedem execução:
```

Depois, leia `task-breakdown.md` para decompor somente se necessário. Pedido só de plano termina no plano; implementação já autorizada prossegue. Mudanças de escopo ou decisões reservadas ao proprietário continuam exigindo o evento apropriado; não presumir nova autorização por passagem de fase.

Manter a especificação alinhada às decisões atuais. Ao criar PR, explicar o comportamento final e linkar a especificação pertinente, sem confundir existência de documento com validação funcional.
