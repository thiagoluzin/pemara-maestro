---
name: video-production
description: "Executa produção e edição técnica de vídeo: inspeção ffprobe/decode, corte, concat, texto gráfico, legendas, áudio autorizado, codecs e integridade. Use para montar, editar, diagnosticar ou entregar arquivos de vídeo; direção artística passa pelo production lead. Intro de jogo com marca usa ai-video-intro-pipeline."
---

# Video Production — execução e integridade

Receba direção de `pemara-video-production-lead` e tabela de montagem de `pemara-film-editor`. Transforme decisões em edição reproduzível, sem decidir dramaturgia, trocar motor ou alterar fontes aprovadas silenciosamente. Completar testes não significa aprovação artística.

<!-- TURBO ENGINE v2 — DO NOT REMOVE -->
## Protocolo de execução

1. Leia AGENTS/spec vigentes, verifique autorização, arquivos, hashes, aprovação exata e restrições da rota. Preserve originais, rejeitados e versões. Não reabrir projeto encerrado.
2. Inspecione os arquivos reais: ffprobe, decode, duração, FPS, frames, codec, cor, resolução e todas as faixas de áudio. Não anunciar que mediu algo só porque o comando está pronto.
3. Compare a tabela de montagem com fontes aprovadas: in/out reais, grade de frames, direção de tela e estados de entrada/saída. Rejeitados não entram como 'melhores trechos'.
4. Não normalizar tudo por hábito. Incompatibilidade de FPS, geometria, cor ou áudio requer decisão explícita e solução qualificada; stream copy somente com bitstreams compatíveis. Preserve o áudio existente.
5. Para filtros complexos já autorizados, verificar um segmento representativo antes do lote, sem promover esse teste. Execução Comfy pelo Codex é exclusivamente MCP `comfyui-local`, com inventário vivo e validação do grafo exato; o backend Maestro mantém seu canal autônomo.
6. Execute sem ocultar exit code. Registre comando, parâmetros, fonte/hash, saída/hash, recibos e alterações em registro do projeto. Não imprimir credenciais.
7. Faça decode e medição da saída completa; revisar visualmente o MP4, contatos/junções e o áudio real quando houver. Contact sheet não basta para afirmar movimento, naturalidade ou sincronismo.
8. Mantenha independentes: integridade técnica, parecer artístico e aprovação do proprietário. Sem acesso temporal/escuta, registre a limitação e os itens pendentes.
<!-- End TURBO ENGINE v2 -->

## Motor, processamento e acabamento

No Maestro, MiniMax H3 é a escolha vigente depois da remoção do LTX. H3 exige SageAttention + Spectrum no caminho de amostragem. Não reinstalar LTX nem oferecer motor alternativo. Fora do Maestro, preserve a stack/motor expressamente escolhidos; esta skill não recomenda contratação ou mudança automática de provedor.

Após a aprovação da fonte ou da montagem, siga o [contrato de âncoras e acabamento de vídeo](../pemara-video-production-lead/references/dlss5-full-frame-required.md). Use os perfis qualificados de FHD, QHD ou UHD conforme a entrega. Confira duração, geometria, áudio e hashes do nativo e do acabado. A fonte silenciosa permanece silenciosa salvo pedido expresso de novo áudio.

Scale/unsharp/Real-ESRGAN não substituem esse acabamento. Nunca alterar duração, corte, transparência, profundidade/cor ou faixas silenciosamente para passar o gate. RIFE não corrige coreografia ou identidade. V8 específico de FFVIII prevalece sobre permissões genéricas de trim/retime.

Usar caminho GPU qualificado para render/encode; para entrega FFmpeg, NVENC conforme política vigente. Indisponibilidade não autoriza fallback CPU/libx264. Stream copy/mux e inspeção leve são CPU permitida. Sem GPU autorizada, preparar comandos e relatórios sem executá-los.

## Comandos de inspeção e operações sem troca criativa

Exemplos para adaptar aos caminhos medidos e ao escopo autorizado; não são comprovação de execução:

```powershell
ffprobe -v error -show_format -show_streams -of json "fonte.mp4"
ffmpeg -v error -i "fonte.mp4" -map 0:v:0 -map 0:a? -f null -
# Concat somente após conferir compatibilidade e aprovação de todas as fontes:
ffmpeg -f concat -safe 0 -i "lista_aprovada.txt" -map 0:v:0 -map 0:a? -c copy "montagem_candidata.mp4"
# Prancha INTERNA para localizar aparência/tempos; não comprova movimento:
ffmpeg -i "fonte.mp4" -vf "select=not(mod(n\,48)),scale=320:-1,tile=6x5" -frames:v 1 -update 1 "qc_interno.jpg"
```

Tabela de corte usa timestamps/frame counts reais; não usar `-shortest` para esconder truncamento nem `-an` para perder áudio. Inspeção silenciosa significa silenciar o player, não remover a faixa da fonte.

Mix/nivelamento só quando autorizado: medir antes/depois, definir alvo pelo destino/spec, preservar voz/Foley aprovados e ouvir o resultado. Um alvo LUFS genérico não comprova qualidade nem autoriza modificar uma trilha aceita. Texto/logo exatos devem vir de assets autorizados/composição determinística, sem depender de texto inventado pelo gerador.

## Saída e revisão

Entregue arquivo candidato com link local absoluto, hashes, comando/recibo, comparação de duração/FPS/frames/áudio e falhas/pendências. Não sobrescrever master. Vincule o recibo ao arquivo exato e registre a procedência das fontes.

Use `E:/Pemara/.agents/skills/pemara-video-production-lead/references/production-quality-contract.md` para a revisão artística; papel técnico não pode declarar que o filme ficou bom apenas por codec/FPS/decode. Aprovação final e publicação são decisões separadas.

Intro/cutscene de jogo com logo/registro mantém `ai-video-intro-pipeline`. Identidade recorrente, combate, movimento e voz carregam seus gates específicos; não transferir regras de um tipo de vídeo para todos os demais.

## Pós-execução ComfyUI — 2026-11-13

Ao concluir uma execução autorizada, aplicar [performance-optimizer](E:/Pemara/.agents/skills/performance-optimizer/SKILL.md), módulo `references/post-comfyui.md`, antes da entrega. Medir em código e usar Decision quando houver julgamento semântico; preservar qualidade, escopo e operação pelo MCP.
