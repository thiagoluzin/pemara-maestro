# Contrato de roteamento Turbo

O registro `turbo_registry.json` separa três conceitos:

- `aliases`: perfis antes idênticos à skill homônima; agora só apontam para a fonte canônica.
- `specialized_profiles`: perfis com conteúdo próprio; permanecem independentes.
- `dispatcher_profile`: perfil mestre que escolhe as skills sem incorporar cópias delas.

Adicionar um alias exige uma skill homônima existente. Adicionar uma especialização exige confirmar que ela difere da skill homônima e documentar no próprio perfil o motivo da diferença.

O Messenger Turbo não substitui a leitura integral da skill selecionada. Ele reduz duplicação, limita o conjunto carregado e registra os gates obrigatórios.
