# Higiene do repositorio Maestro

O Git guarda codigo-fonte, configuracoes sem segredo, testes e documentacao.
Modelos, midias, bancos, logs, filas, saidas, ambientes virtuais e builds ficam
no disco de trabalho e sao excluidos pelo `.gitignore` da raiz.

Essa separacao evita commits gigantes sem apagar o historico operacional. Se um
arquivo de execucao tiver sido rastreado por engano, use `git rm --cached` para
retira-lo apenas do indice; nunca apague o original como parte da higiene.

Antes de preparar uma entrega:

1. confira `git status --short`;
2. verifique se nao ha segredo ou artefato grande entre os arquivos preparados;
3. execute os testes focados e o smoke test do servico;
4. empacote APKs e outras midias fora do conjunto versionado.
