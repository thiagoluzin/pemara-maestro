# Continuidade de identidade em clipes com personagens recorrentes

Contrato `pemara-character-bible@1`, introduzido em 2026-09-08 após o encerramento do R17.
Objetivo: preservar identidade entre takes sem perder física, iluminação, água e realismo.
Não garante consistência por configuração: as imagens continuam exigindo revisão visual.

## Responsabilidades

| Função | Entrega |
| --- | --- |
| Continuidade | Ficha canônica, referências e hashes, estado de entrada/saída, revisão das âncoras |
| Combate | Ação, câmera, contatos e poderes compatíveis com a ficha fixa |
| QC | Comparação com ficha original e take anterior; avaliações independentes por dimensão |
| Proprietário | Direção e decisão artística sobre o artefato exato |

Não é necessário criar agentes adicionais. As quatro skills live-action existentes apontam para este contrato.

## Uso real no workflow

1. Copie os templates de `templates/identity_continuity/` para a nova produção. A ficha possui referências de frente, perfil, costas e detalhes conforme disponíveis. Registre lacunas; não invente vistas aprovadas.
2. Identifique cada referência por caminho, SHA-256, papel `canonical`, `ownerApproved: true` e `approvalEvidence` real. Frame extraído de take aprovado é candidato a referência até decisão explícita nesse escopo.
3. No spec de `compile_live_action_plan`, use `identityContinuityRequired: true` e `identityContinuity` preenchido. Specs legados continuam compatíveis; animação avulsa de foto não usa este contrato. A regra de autoria exige ativá-lo em novos clipes recorrentes; não há migração silenciosa nem interceptação de todos os envios do Maestro.
4. Caminhos de bible/âncoras/estado anterior são relativos ao workspace fornecido ao compilador, ou absolutos. Referências dentro da ficha são relativas ao diretório da própria ficha, ou absolutas.
5. O compilador verifica arquivos/hashes, personagens, aprovação registrada das referências, revisão de âncoras vinculada aos hashes e evolução de estado. `build_live_action_comfy_graph` insere o bloco fixo antes do texto de ação/câmera. Correções de ação não editam a ficha. Conflitos semânticos no texto variável continuam exigindo revisão; não existe detector automático de identidade aqui.
6. Mantenha a resolução/passos/quadros do contrato escolhido. Para H3, confira SageAttention conectado e valide o grafo exato por MCP. Esta compilação local não inicia geração nem substitui admissão GPU.
7. Revise o MP4 inteiro, contatos e fronteiras. O template de revisão registra início/meio/fim como índice de evidência; três amostras não provam a física do clipe inteiro. `validate_candidate_review` confere integridade do registro, não assiste ao vídeo. Chame-o antes de selecionar a mídia; FAIL/PENDING impede seleção pelo contrato. Ele não intercepta automaticamente uma montagem executada por outro caminho.
8. Salve `exitState` do plano como JSON vinculado por hash. O take seguinte deve declarar `previousState`; a entrada deve ser idêntica à saída anterior. Secagem/limpeza/cura dentro de um take requer `physicalChangeReason`. Mudanças fora de cena precisam ser planejadas e documentadas, não apagadas da tabela.

## Evidência e decisões

`EVIDENCE_VALIDATED_NOT_ARTISTIC_APPROVAL` significa somente que o contrato e os arquivos conferem.
Identidade, combate, física, iluminação, água e realismo recebem PASS/FAIL/PENDING; NOT_APPLICABLE serve apenas para dimensões que não aparecem, nunca identidade.
A aprovação artística permanece separada, por arquivo/hash. Não converter encerramento do projeto em aprovação retroativa de todos os takes ou âncoras.

## Pacote de encerramento

Preserve mídia final e hashes; registre feedback literal, aspectos a preservar, referências derivadas como candidatas, lacunas de vistas e próximos passos. A ficha do R17 é uma retrospectiva provisória: não está liberada automaticamente como referência canônica de outro projeto.

O Maestro continua usando a mídia final registrada. O pacote de encerramento fica no projeto e é vinculado no manifest; este trabalho não cria um novo editor visual de comparação no player nem reinicia o servidor. Para revisar, abra referências e candidato lado a lado e registre a decisão no template. Uma interface dedicada pode consumir o mesmo contrato posteriormente.

## Etapa zero: pesquisa antes de produzir

Para personagem existente, preencher `origin: existing` e `research` ANTES de construir a ficha definitiva e as âncoras. Fixar versão (obra/edição/encarnação/traje), reunir fontes primárias e mapear cada tópico às fontes que o sustentam. Registrar data da consulta, escopo de versão, resumo factual, lacunas e adaptações autorizadas separadamente. Uma fonte que só lista o personagem não prova seus materiais, todos os golpes ou poderes.

O gate exige os cinco tópicos, fonte primária ou justificativa de indisponibilidade, revisor e ausência de dúvidas bloqueantes. Não verifica a verdade da pesquisa automaticamente. `REVIEWED` só deve ser escrito depois de examinar o material; nunca preencher com placeholders para liberar render. Não é preciso saber cada dado imaginável: é preciso cobrir o que a cena mostrará e declarar o que não se sabe. Mudança de edição, traje ou poderes reabre a pesquisa e versiona a ficha.

Ordem: pesquisa → versão e adaptações → ficha canônica → estados → âncoras → prompt → validação → geração autorizada → QC → decisão artística. Para personagens originais, `origin: original` usa o design aprovado pelo proprietário, sem inventar pesquisa de cânone.

## Execução offline

A partir de `maestro/pemara`, com o Python do Studio:

```powershell
python ferramentas/video_global_engine/tools/identity_continuity_gate.py --spec CAMINHO_SPEC.json --report preflight_identity.json
python ferramentas/video_global_engine/tools/identity_continuity_gate.py --review CAMINHO_REVIEW.json --bible CAMINHO_BIBLE.json --report candidate_identity_gate.json
```

O primeiro comando exige o contrato, inclusive se o spec omitiu a flag. O segundo retorna código 1 se há FAIL/PENDING ou se a reprodução integral/contatos não foi registrada. Código 0 é apenas evidência revisada; não autoriza GPU nem substitui aprovação artística. Não execute o gate de seleção sem observações reais do MP4.

Antes de preparar ancoras, confira primeiro somente o dossie:

```powershell
python ferramentas/video_global_engine/tools/identity_continuity_gate.py --research character_bible.json --report research_gate.json
```

Isso permite verificar a pesquisa antes de existir qualquer imagem nova. O pacote retrospectivo R17 deve falhar nesse gate enquanto a versao canonica estiver indefinida; essa lacuna nao reabre o projeto encerrado.
