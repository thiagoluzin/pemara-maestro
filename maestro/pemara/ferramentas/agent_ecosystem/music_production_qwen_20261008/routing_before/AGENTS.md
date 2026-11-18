## Remocao do LTX autorizada pelo proprietario - 2026-10-08

Ordem vigente: tirar o LTX do Maestro e apagar seus pesos e programas exclusivos, sem afetar outros motores. O registro ativo e o seletor do Maestro permitem somente MiniMax H3, com escolha explicita e sem fallback. Esta ordem substitui as instrucoes anteriores de manter o seletor H3/LTX para novas geracoes. Takes antigos, midias e projetos permanecem preservados; perfis LTX historicos nao podem gerar nem ser convertidos automaticamente para H3.

Preservar o ComfyUI e as dependencias compartilhadas: operacoes basicas LTXVSeparateAVLatent/LTXVConcatAVLatent usadas pelo H3, Gemma4 E2B usado pelo avaliador do Creative OS, pre-processadores de profundidade, audio e acabamento. Nomes com LTX em codigo compartilhado nao autorizam remocao. Nao reinstalar pesos ou a extensao ComfyUI-LTXVideo automaticamente. Evidencias e inventario: cleanup_manifests/ltx_removal_20261008/.

# Instruções do projeto

Pragmático e coerente.


## Produção de vídeo: agentes e skills - 2026-10-08

Para novos pedidos de criação, direção, melhoria ou revisão de vídeos, começar com `E:/Pemara/.agents/skills/pemara-video-production-lead/SKILL.md`. Dirigir a sequência antes do prompt e carregar atuação (`pemara-performance-director`), fotografia (`pemara-cinematography-director`) e montagem (`pemara-film-editor`) conforme a fase. Manter os especialistas existentes de combate, continuidade, movimento, voz e QC.

Esses são papéis que um mesmo agente pode executar; não exigem subagentes. Planejamento completo e testes técnicos não comprovam qualidade artística. Revisar os arquivos reais com evidências temporais e preservar a aprovação exata do proprietário, os aspectos aprovados, o motor H3 com Sage + Spectrum e o acabamento obrigatório. Atualização de método não autoriza render ou reabertura de projetos encerrados.

## Upscaling obrigatório aprovado — 2026-10-06

Regra expressa do proprietário: "mota esse worflow completo e salva como upscaling obriagotorio". Referência aprovada: "SeedVR2 3B + RIFE exato 60 FPS + DLSS 5 + Foley, melhor de todos".

- Novos jobs de upscale e acabamentos finais de vídeo devem usar o contrato `maestro/pemara/services/studio/upscaling_required.py`: SeedVR2 3B int8, RIFE 4.25 em timestamps j/60, DLSS 5 Natural e cópia do áudio existente. Não substituir silenciosamente por RealESRGAN, UltraSharp, SeedVR2 7B ou duplicação simples de quadros.
- Preservar o vídeo nativo e o gate de aprovação da fonte antes do upscale. H3/LTX, Sage + Spectrum, duração e direção permanecem os escolhidos. O acabamento gera outro candidato, sujeito à avaliação própria do proprietário.
- Perfis em `maestro/pemara/ferramentas/video_global_engine/upscale_profiles/seedvr2_3b_rife_exact60_dlss5_foley_v1_*.json`: FHD, QHD e UHD, paisagem/retrato, contain/pad sem corte. FHD vertical é a referência RE1 aprovada; outras resoluções exigem revisão de seu resultado, sem afirmar qualidade aprovada por extrapolação.
- Foley existente é preservado; a regra não autoriza criar áudio para uma fonte silenciosa. SDR 8-bit, CFR 24..60 FPS, duração alinhada a 1/60 s e até uma faixa de áudio são os limites atuais; incompatibilidade bloqueia sem descarte ou conversão silenciosa.
- Preservar perfis antigos, mídia histórica e projetos encerrados. Não migrar nem renderizar produções anteriores automaticamente. Codex valida/envia pelo MCP; o worker do Maestro opera autonomamente pelo backend.

## DLSS 5 obrigatório no acabamento visual — 2026-10-06

Regra expressa do proprietário: "dlss5 melhorou a imagem sim, pode colocar ele de forma obrigatoria nos workflows".

- Toda nova saída de imagem ou vídeo deve passar pelo DLSS 5 Neural Rendering antes da entrega. Aplicar também a grafos importados/repetidos, upscale, editor, remaster e novos masters.
- Usar o perfil aprovado no comparativo RE1: Natural, NR 1x, intensidade 0.5, estrutura 0.5, tom 0, pele 0.25, detalhe 0.5, cor 0 e auto-mask ligado. Preservar os motores escolhidos, Sage + Spectrum, geometria, FPS, duração, transparência e áudio.
- Preservar a fonte anterior e um recibo com hashes e comprovação da execução do NR. Ausência, incompatibilidade ou falha bloqueia a entrega sem fallback silencioso. Formatos/profundidades ainda não qualificados ficam bloqueados até qualificação.
- Arquivo já tratado com recibo válido não recebe outra passagem automaticamente ao copiar, multiplexar, criar proxy ou concatenar bitstreams tratados. Verificar a herança do tratamento.
- Não modificar entregas históricas nem reabrir projetos encerrados. Aprovação do efeito no RE1 não aprova artisticamente outras mídias.

## Identidade visual em produções com continuidade — 2026-09-08

- Para novos clipes com personagens recorrentes, usar o contrato `ferramentas/video_global_engine/docs/IDENTITY_CONTINUITY.md` no workspace `maestro/pemara` e declarar `identityContinuityRequired: true` no spec de produção. Não aplicar essa exigência à animação avulsa de foto nem migrar projetos antigos automaticamente.
- Continuidade mantém ficha canônica por personagem e estado por take; direção de combate altera ação/câmera sem reescrever identidade; QC compara início, meio, fim e contatos com a referência original e a fonte anterior. São responsabilidades, não obrigação de criar subagentes.
- Referências têm caminho, hash, escopo e evidência de aprovação. Derivar quadro de vídeo aprovado não aprova automaticamente esse quadro como referência canônica. Rejeitados nunca alimentam novas âncoras ou montagem.
- O último quadro fornece pose e movimento; a referência original continua sendo o padrão de rosto, proporções, traje e materiais. Não acumular deriva usando apenas o último resultado.
- Registrar entrada/saída de sujeira, umidade e danos. Limpeza, secagem ou recuperação exigem causa narrativa explícita; danos não desaparecem por troca de take.
- Separar identidade visual, combate, física, iluminação, água e realismo no QC. Integridade de arquivos e checklist não comprovam fidelidade nem aprovação artística. Crítica de identidade preserva os outros aspectos aprovados.
- Projeto declarado finalizado fica encerrado para geração automática. Aprendizados e regras podem ser registrados sem reabrir a produção ou alterar a mídia entregue; novo render exige nova direção explícita.

## Correção de takes após crítica — 2026-09-07

Regra expressa do proprietário: toda vez que ele apontar o que ficou ruim em um
take, corrigir e gerar uma nova tentativa do mesmo escopo automaticamente, sem
aguardar outro pedido "faça o vídeo". Preservar os aspectos aprovados e os
arquivos rejeitados. Conferir fila/GPU e validar o workflow pelo MCP antes de
enviar. Uma nova ordem explícita de pausa ou "sem gerar" prevalece. A nova mídia
continua sujeita à avaliação artística do proprietário; crítica não autoriza
montagem, publicação, troca de motor ou ampliação do escopo.

## MiniMax H3 — SageAttention obrigatório (2026-09-07)

Atualização expressa do proprietário em 2026-10-04: "Colocar em todos os workflow sage+ spectrum. Obrigatório sempre".

- Toda próxima geração H3, em qualquer perfil, orientação, duração ou modo, exige SageAttention + Spectrum efetivamente ligados no caminho de amostragem. Usar a configuração Spectrum audio-replay aprovada em `maestro/pemara/services/studio/h3_spectrum_master20.json`, com a proteção Sage de quatro grupos antes do Spectrum.
- Spectrum deixou de ser opcional ou restrito ao perfil Master20. Preservar resolução, passos, áudio e motor escolhidos; não empilhar FirstBlockCache. IDs antigos de perfis FBC/Spectrum resolvem para Master com Sage + Spectrum nas novas gerações.
- Aplicar a regra aos builders e no envio final do Maestro, incluindo importação e repetição de grafos. Nó ausente ou combinação incompatível bloqueia a geração, sem fallback silencioso. RES multistep é o sampler qualificado; combinações adicionais exigem validação antes de uso.
- Preservar grafos históricos, benchmarks e mídia entregue. Aprovação do take Leon/Licker Spectrum é daquele artefato; não aprova automaticamente outras cenas.

Regra expressa do proprietário: "SageAttention isso é obrigatorio sempre".

- Toda próxima geração H3 deve usar SageAttention compatível e efetivamente conectado ao transformer. Não voltar silenciosamente à atenção nativa para concluir um render.
- Verificar o nó no runtime ativo e sua ligação no grafo, não apenas a instalação em disco. Validar o grafo exato por MCP antes de enviar.
- Para R17, preservar resolução, quadros e passos do contrato; preferir o patch isolado do H3 usado na A11. Não substituir por patch global ou reduzir qualidade sem direção explícita.
- Nó ausente exige corrigir a integração antes da geração. A rejeição artística de uma mídia não revoga a otimização técnica.
- Esta regra não altera a escolha de motor H3/LTX do proprietário nem autoriza geração de outro escopo por si só.

## Restrição temporária de GPU — 2026-09-07

O proprietário suspendeu o uso durante o jogo e depois liberou explicitamente: "Gpu liberada". Os testes de implantação com GPU podem prosseguir via MCP, com nova verificação do estado atual. O benchmark `4680c104-7a5b-41b5-b620-76ff37b5ada7` permanece cancelado no histórico; a retomada usa uma nova tentativa identificada.

## ComfyUI: coordenação pelo Codex e uso direto do Maestro

Regra expressa do proprietário em 2026-09-07:

- Exceção expressamente autorizada posteriormente: o Codex pode usar terminal para configurar e instalar o necessário à implantação, incluindo manutenção do runtime e do MCP. As operações de geração do Codex (validar, enviar, acompanhar, cancelar e obter resultados) permanecem exclusivamente via MCP. Essa exceção não altera a autonomia do Maestro nem a escolha do motor pelo proprietário.

- Quando o Codex coordenar ou operar o ComfyUI, toda interação com o serviço deve ocorrer exclusivamente pelo MCP `comfyui-local`: inventário vivo, saúde, validação, envio de workflow, acompanhamento, cancelamento e obtenção de resultados, além de operações de runtime quando autorizadas.
- Não contornar MCP com HTTP direto, curl, requests, urllib, scripts/CLI ou navegador para realizar essas operações. A leitura de código, configurações e arquivos locais para Discovery continua permitida; isso não autoriza executar um cliente direto disfarçado de inspeção.
- Se o MCP estiver indisponível ou seu estado for ambíguo, informar o bloqueio e preservar os trabalhos existentes. Não assumir fila vazia, reenviar jobs, interromper processos ou trocar o canal de operação silenciosamente.
- Começar por `server_info` e distinguir o workspace em disco do runtime ativo. Catálogo e histórico persistido não comprovam capacidade executável ou fila viva. Validar o workflow por MCP antes de qualquer geração autorizada.
- Quando o proprietário usar a interface do Maestro para gerar um vídeo, o backend pode continuar enviando e acompanhando diretamente no ComfyUI. Esse fluxo é autônomo e não depende de uma sessão do Codex; não migrá-lo para MCP nem criar monitor do Codex apenas por causa desta regra.
- A escolha do motor no Maestro pertence ao proprietário. Preservar o seletor explícito de MiniMax H3 e LTX 2.5, sem motor imposto, troca automática ou fallback silencioso. Indisponibilidade do motor escolhido deve ser informada, sem substituí-lo. Não remover essa escolha ao integrar Creative OS ou qualquer roteador futuro.
- Monitor pelo Codex só deve ser criado quando houver solicitação específica de acompanhamento adicional. Esta regra não autoriza render, instalação, download, cleanup, restart, aprovação de mídia ou mudança de workflow por si só.

## Pesquisar personagens existentes antes de produzir — 2026-09-08

- Regra do proprietário: pesquisar antes de fazer, usando personagens existentes para aprimorar o processo. Antes de roteiro detalhado, ficha definitiva, prompts, âncoras ou geração, reunir especificações documentadas da versão escolhida.
- Identificar obra/jogo/filme, edição, época, traje/skin e encarnação; não misturar versões. Pesquisar aparência/proporções, roupa e materiais, mecanismos de combate, poderes/limites e personalidade/movimento. Não inventar medidas ou detalhes não publicados.
- Priorizar fontes oficiais, material original e gameplay/trailers da edição correta. Registrar URL, título, data de consulta, versão coberta e quais afirmações a fonte sustenta. Wiki/fan art são apoio identificado, não prova canônica isolada. Ausência de fonte primária exige motivo registrado.
- Separar fatos pesquisados, inferências e adaptações dirigidas pelo proprietário. Dúvidas críticas de versão ou identidade devem ser resolvidas antes de âncoras; lacunas secundárias permanecem declaradas.
- O dossiê alimenta a ficha fixa. `origin: existing` exige `research` revisado no contrato; validar JSON não prova que uma fonte foi lida nem que o visual está fiel. Revisor precisa examinar fontes e imagens reais.
- Esta regra não autoriza treino/LoRA, download de modelos, GPU ou nova mídia por si só. Projeto finalizado permanece encerrado.
