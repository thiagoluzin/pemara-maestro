# Baseline de controles

## Índice

1. RLS e isolamento
2. Regras de negócio no servidor
3. IDOR e autorização por objeto
4. Segredos
5. Inputs, XSS e uploads
6. Controles estendidos
7. Evidência mínima por mudança

## 1. RLS e isolamento

- Enumerar todas as tabelas/coleções que carregam `tenant_id`, usuário ou organização.
- Habilitar e forçar RLS no Postgres quando a aplicação usar multitenancy.
- Criar políticas por operação; não depender apenas de filtro do ORM.
- Definir o contexto de tenant a partir da identidade autenticada, nunca de body/query/header controlado pelo cliente.
- Testar com duas identidades: A acessa A; A não lê/muta B; B não lê A.
- Em Supabase/BaaS, revisar tabela por tabela, inclusive storage e funções RPC.
- Para arquitetura single-tenant/SQLite, usar `not_applicable` somente com evidência do modelo e autorização por usuário onde existir.

## 2. Regras de negócio no servidor

- Recalcular preço, desconto, total, frete, estoque, quota e custo no backend.
- Resolver `role`, `ownerId`, `tenantId`, `paid`, `status` e permissões a partir de identidade/política persistida.
- Usar schemas com allowlist; nunca repassar body inteiro para create/update.
- Tratar localStorage, campos hidden e flags do frontend apenas como estado de interface.

Testes: adulterar preço/papel/status; chamar endpoint sem o botão da UI; repetir requisição concorrente.

## 3. IDOR e autorização por objeto

- Condicionar toda busca/mutação a recurso + usuário/tenant/política.
- Não autorizar porque o ID é UUID ou difícil de adivinhar.
- Cobrir downloads, arquivos, jobs, imagens, pedidos, pacientes, takes e rotas administrativas.
- Testar IDs existentes de outra identidade em URL, query, JSON e nomes de arquivo.

## 4. Segredos

- Manter chaves em secret store ou `.env` privado fora do Git e do frontend.
- Verificar árvore atual e histórico; redigir saída do scanner.
- Revisar Docker image/layers, bundles, source maps, logs, backups e artefatos de CI.
- Se um segredo real foi versionado ou publicado, remover não basta: rotacionar e registrar a revogação.
- Não inserir `.env`, token ou chave no contexto de LLM/agente.

## 5. Inputs, XSS e uploads

- Validar schema, tamanho, faixa, enumeração e comprimento no servidor.
- Usar query parametrizada e argv sem shell para dados externos.
- Renderizar texto com escaping/`textContent`; sanitizar HTML somente quando HTML for requisito explícito.
- Bloquear SVG/HTML executável salvo como imagem, salvo sandbox dedicado.
- Conferir magic bytes e decodificar o conteúdo; não confiar em extensão ou MIME do navegador.
- Gerar nome no servidor, impedir traversal e servir upload com no-sniff e sem execução.
- Proteger parser XML contra DTD/entidades e ZIP contra decompression bomb.

## 6. Controles estendidos

- Autenticação/sessão: hash forte, expiração, issuer/audience, cookie HttpOnly/Secure/SameSite, CSRF e rate limit.
- Mass assignment: DTO/schema allowlist e campos sensíveis impossíveis de enviar.
- Concorrência: transação, constraint, lock e idempotency key para estoque, pagamento, quota e jobs.
- Infra: Host allowlist, origem loopback atrás de gateway, CORS mínimo, debug off, headers defensivos e stack trace oculto.
- Agente/LLM: schema antes de ferramenta, menor privilégio, auditoria, limites e aprovação humana.
- Dados: backup restaurável, comparação objetiva e ausência de perda comprovada.

## 7. Evidência mínima por mudança

| Mudança | Evidência obrigatória |
|---|---|
| Rota por ID | teste mesma identidade + identidade diferente |
| Admin/papel | chamada direta sem UI + papel forjado |
| Preço/estoque | valor adulterado + concorrência/transação |
| Upload/input | tamanho, tipo real, payload inválido e XSS escapado |
| Segredo | Gitleaks redigido + confirmação/rotação quando real |
| Publicação | origem, proxy, DNS, headers, Host inválido e listener |
| Banco/migração | dump, restauração temporária e comparação |
| Agente/LLM | output malformado, tentativa de path/shell e limite de ação |

Scanner aprovado não substitui estes testes de comportamento.
