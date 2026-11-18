# Entrada atual de restauracao de modelos — 02/11/2026

O GitHub nao contem pesos. Os BATs e manifestos ficam versionados para restaurar os modelos no computador de destino. Nao foram executados downloads ou renders nesta entrega.

Use `INSTALAR_PILHA_ATUAL.bat` para os instaladores H3, Qwen, avaliador compartilhado Gemma4, Foley e RIFE 4.25. Para simular os comandos sem baixar: `INSTALAR_PILHA_ATUAL.bat --dry-run`. As dependencias Python/GPU do sistema precisam ser restauradas antes. Para o download RIFE, instale `python -m pip install gdown==6.1.0`; alternativamente passe um ZIP oficial ja baixado a `05_INSTALAR_RIFE_425_ATUAL.bat --archive C:\caminho\rife425.zip`.

RIFE 4.25 e conferido pelo mesmo SHA-256 exigido por `services/studio/rife_required_runner.py`; outra versao bloqueia sem substituir a existente. O instalador aceita somente o peso esperado do ZIP, sem extracao de caminhos arbitrarios, e usa as tres fontes Python do runtime qualificado preservadas em `rife425_source/`. A licenca MIT do fornecedor acompanha essas fontes. Dependencias como PyTorch pertencem ao ambiente GPU existente; nao sao trocadas automaticamente.

Fonte primaria consultada em 02/11/2026: [Practical-RIFE, lista oficial de modelos](https://github.com/hzwer/Practical-RIFE#trained-model). Licencas e disponibilidade futura dos fornecedores continuam aplicaveis. Fontes HF restritas podem exigir a conta/token do proprietario, somente pelo ambiente local.

`INSTALAR_TUDO_MODELOS.bat`, `03_INSTALAR_RIFE_FHD60.bat` e o README anterior foram preservados como historico. Eles incluem RIFE 4.6/RealESRGAN e **nao sao a entrada da pilha vigente**. A entrada atual nao chama essa etapa. Os demais BATs e PS1 existentes estao inventariados em `workflow_catalog/installers.json` no repositorio.

Politica vigente: H3 com SageAttention + Spectrum; RIFE 4.25 em 60 FPS exatos quando autorizado; live action com Lanczos + NVENC; SeedVR2 somente em animation; DLSS 5 somente em ancoras. Workflows antigos com motores removidos ou outra politica sao historicos, nao permissao para reativar ou renderizar. Instaladores especificos de outros recursos permanecem junto de seus componentes; nenhum modelo e baixado por abrir o repositorio ou consultar o catalogo.
