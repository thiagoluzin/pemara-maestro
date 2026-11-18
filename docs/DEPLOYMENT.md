# Implantação segura

## 1. Inventário e backup

Registre versões, commits, hashes, portas, espaço e estado da fila. Faça backup
dos scripts, regras e manifests antes de alterar o runtime; não duplique pesos
de modelos no backup.

## 2. Runtime isolado

Instale ComfyUI, Python, PyTorch e CUDA em uma versão isolada. Não substitua o
runtime ativo sem healthcheck e rollback. Mantenha o bind em loopback.

## 3. Modelos

Baixe somente após ação explícita do operador. Verifique revisão, tamanho e
SHA-256. Pesos não pertencem ao Git.

## 4. Motores

Materialize dois adapters: `minimax_h3` e `ltx_2_5`. O seletor deve exigir uma
escolha e persistir o ID no job/take. Não implemente fallback.

## 5. LTX 2.5

Fixe a revisão do modelo, o commit do custom node e os workflows oficiais.
Bloqueie engine, checkpoint e workflow LTX 2.3. IC-LoRAs 2.3 só podem entrar
pela allowlist de compatibilidade do LTX 2.5.

## 6. Smoke e promoção

Execute um job mínimo com fila vazia, lease exclusiva e âncora técnica sem
dados pessoais. O recibo precisa conter engine, modelo, node commit, workflow,
hash do output, QC técnico e `fallback_used=false`. A promoção é técnica;
qualquer take real continua dependente de revisão humana.
