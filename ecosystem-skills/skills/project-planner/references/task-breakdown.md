# Dependências e incrementos verificáveis

Receba requisitos e escopo já estabelecidos. Leia componentes reais antes de estimar impacto. Uma correção pequena com caminho claro não precisa de um segundo plano.

1. Mapeie dependências duras: dados/schema → tipos/serviço → consumidor → interface/entrega. Não imponha banco, frontend ou mobile a todo projeto.
2. Prefira incrementos que entreguem um comportamento verificável de ponta a ponta. Evite terminar todas as camadas isoladas sem uma rota funcional.
3. Antecipe o maior risco e planeje sua verificação antes de multiplicar a estratégia.
4. Para cada tarefa registre objetivo, entrada, saída, aceite, arquivos prováveis, dependências e comando/observação de verificação. Divida tarefas quando o aceite ficar difuso, não só por contagem de arquivos.
5. Feche checkpoints em mudanças de dependência ou risco. Use a autorização existente; revisões não devem virar pedidos repetidos de confirmação.
6. Arquivos compartilhados, schema/consumidor e migrações são sequenciais. Trabalhos independentes só podem ser delegados quando autorizado. O mesmo agente pode cumprir os papéis.

```text
Tarefa:
Por que existe / resultado observável:
Entrada e dependências:
Arquivos/componentes prováveis:
Aceite:
Verificação real:
Recuperação se falhar:
Estado e evidência:
```

Plano final: objetivo → decisões → tarefas ordenadas → riscos/recuperação → verificações → pendências. Use o local já adotado pelo projeto. `tasks/plan.md` e `tasks/todo.md` são obrigatórios somente para integrações que realmente os consomem; não duplique um plano existente com outro nome.

Antes de executar, confirme que cada dependência tem fornecedor, cada tarefa tem aceite e os comandos existem. Marque concluído somente após evidência. Ao encontrar erro concreto, preserve reprodução e corrija a dependência antes de trabalho que depende dela; trabalho independente pode continuar.

Conclusão exige aceite atendido, verificações afetadas executadas e evidência registrada. Critérios específicos do projeto prevalecem; documento preenchido não comprova execução.
