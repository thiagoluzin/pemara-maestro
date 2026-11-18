# DLSS 5 em âncoras e acabamento de vídeo

A ordem de 22/10/2026 reserva o DLSS 5 às **novas âncoras e imagens-base da produção**. Declare `content_kind` como `live_action`, `mixed` ou `animation` antes do render. Tipo ausente ou conflitante bloqueia o processamento. A classificação depende da produção e do papel do arquivo.

## Âncora ou imagem-base

Aplique o perfil Natural em todo o quadro, inclusive atores, criaturas e cenário. Use escala NR 1×, intensidade 1, estrutura 1, pele 1, detalhe/composição 1, tom 0, cor 0, `auto_mask=false` e cobertura de 100%, sem máscara de exclusão. No ComfyUI, a referência é o [grafo de âncora integral](../../../../maestro/pemara/ferramentas/video_global_engine/workflows/upscaling_obrigatorio/dlss5_full_frame_anchor.template.api.json). Declare `PemaraDLSS5ContentPolicy(content_kind, stage=final)` e valide o grafo pelo MCP antes de uma execução autorizada.

Preserve o original, o alfa e a geometria. Verifique o recibo do perfil `dlss5_required_full_frame_20261010_v1`, a execução real e os hashes da fonte e da saída. Falha impede a entrega da âncora tratada. Reutilize uma âncora com recibo válido sem uma segunda passagem. A revisão humana de identidade e aparência continua necessária.

## Vídeo

Takes, previews, conectores, proxies, montagens, masters e quadros de vídeo ficam fora do DLSS 5. Extrair quadros para tratá-los e recompor o vídeo também é proibido. Após aprovação da fonte e autorização do acabamento, escolha a rota pelo `content_kind`.

| Tipo | Acabamento |
|---|---|
| `live_action` ou `mixed` | RIFE 4.25 a 60 FPS exatos, redimensionamento por Lanczos e codificação NVENC. SeedVR2 e restauração neural espacial substituta são proibidos. |
| `animation` | SeedVR2 3B int8 e RIFE 4.25 a 60 FPS exatos na rota de upscale. |

As duas rotas preservam duração, geometria e áudio existente. Verifique os hashes da fonte e da saída e o recibo de acabamento com `dlss5_applied=false`. O arquivo acabado é um novo candidato à revisão. O tratamento da âncora continua associado ao seu próprio arquivo.

As ordens de 09/10 e 10/10 e seus recibos permanecem como histórico. Preserve fontes anteriores, versões aprovadas e rejeitadas. Esta política não reabre produções nem aciona novo render. Os contratos executáveis são a [política de conteúdo](../../../../maestro/pemara/services/studio/dlss5_content_policy.py), o [perfil da âncora](../../../../maestro/pemara/services/studio/dlss5_finishing.py) e o [acabamento de vídeo](../../../../maestro/pemara/services/studio/upscaling_required.py).
