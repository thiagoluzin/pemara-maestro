# Maestro PEMARA

Cópia pública de 17 de novembro de 2026. Inclui o aplicativo Windows, o gateway,
os serviços do Studio, a interface e o aplicativo Android do Maestro, as
ferramentas de mídia, o catálogo de workflows e os scripts de instalação.

- [Sistema Maestro](maestro/pemara/)
- [Instaladores dos modelos e ferramentas](maestro/pemara/tools/model_installers/)
- [Catálogo de workflows com SHA-256](workflow_catalog/index.json)
- [Inventário de scripts](workflow_catalog/installers.json)
- [Supervisor Windows](infra/radar/)

A instalação exige configurar os caminhos e as dependências da sua máquina.
Os pesos de modelos são obtidos pelos instaladores. A cópia não inclui
credenciais, bancos em uso, sessões privadas ou mídias geradas.

Para usar um ambiente Python dedicado ao Studio, copie
`maestro/pemara/sistema/studio-web-runtime.example.json` para
`studio-web-runtime.json` no mesmo diretório e informe o executável instalado.

O catálogo público preserva os workflows revisados. Campos de credenciais e
mídia incorporada foram retirados quando presentes. Logs de execução, dados
privados e o histórico Git de operação permanecem no arquivo privado.
