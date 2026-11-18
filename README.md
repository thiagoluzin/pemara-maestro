# Maestro PEMARA

Consulte [o conteúdo do backup público](BACKUP_PUBLICO.md), incluindo o sistema Windows, o Studio, as ferramentas e os workflows.

---

# Maestro — snapshot privado atualizado em 02/11/2026

Este repositorio e privado. A copia atual do sistema Windows esta em [maestro/](maestro/), com o [Harness](pemara_harness/) e as [skills do ecossistema](ecosystem-skills/). O core Turbo anteriormente versionado em src/, configs/ e tests/ foi preservado; as suas referencias historicas nao alteram as ordens atuais do proprietario.

## Restauracao atual

- [Instaladores atuais de modelos](maestro/pemara/tools/model_installers/README_ATUAL.md): BATs, codigo e manifestos, sem pesos. Entrada: `INSTALAR_PILHA_ATUAL.bat`. RIFE 4.25 com SHA-256 fixo; os instaladores antigos 4.6/RealESRGAN permanecem identificados como historicos.
- [Catalogo dos 12.780 workflows/variantes](workflow_catalog/index.json): JSONs existentes e grafos extraidos de PNGs, preservando origem e hash. Modelos e imagens nao estao embutidos. Pastas ignoradas pelo Git foram examinadas; o catalogo inclui as pastas vinculadas conferidas em linked_scan.json; caches/dependencias instaladas e backups antigos ficam fora da descoberta inicial.
- [Scripts BAT/CMD/PS1](workflow_catalog/installers.json) e [referencias de modelos](workflow_catalog/model_references.json). Muitos workflows sao historicos: abrir o catalogo nao autoriza reativar motores removidos ou gerar midia.
- [Pesquisa com fontes no Maestro](maestro/pemara/docs/PESQUISA_COM_FONTES.md), incluindo a integracao atual Firecrawl MCP/TypeSafe e revisao humana.

H3 permanece com SageAttention + Spectrum. LTX removido permanece inativo. Acabamento autorizado: RIFE 4.25/60 FPS exatos; live action Lanczos + NVENC; SeedVR2 somente em animation; DLSS5 somente em ancoras. Preservar fontes e audio e exigir revisao humana. Estes fontes/instaladores nao certificam uma restauracao completa em outro computador.

Credenciais, .env reais, bancos de usuarios, conversas e pesos ficam fora deste snapshot GitHub. O backup local privado no disco G preserva o estado operacional e arquivos sensiveis em pacote separado protegido pelo Windows DPAPI. Uma instalacao restaurada exige configuracao local de credenciais, dependencias e caminhos. PEMARA EDU mantido por ultimo, sem mudancas.
