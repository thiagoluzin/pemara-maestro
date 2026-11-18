# Performance audit — motores existentes

Dois renders locais reais, enviados/validados/acompanhados e obtidos exclusivamente via MCP. Configurações e observações em dados/creative_os/benchmarks/20260907. Não houve instalação de componentes.

| Campo | H3 REFERENCE | LTX REFERENCE |
|---|---|---|
| Motor | FL2VA pruned INT8 ConvRot | 2.5 22B distilled NVFP4 |
| Encoder | Qwen3VL32B NVFP4 AWQ | Gemma4 12B INT8 ConvRot |
| Perfil | Production 1088x608 / 10 steps | two-stage distilled 960x544 → 1920x1088 |
| Quadros / fps / duração | 124 / 24 / 5,166667 s | 121 / 24 / 5,041667 s |
| Áudio | desligado | desligado |
| Seed | 20260907 | 20260907 |
| Hash grafo original | 60d3136a4d04899ecbc9dfdaf930c65126509be71b03ebac8388237851f089b5 | 453e93fddbe33005906feff4e750477810ea1933401f33f803c6c25c91ed6a1b |
| Resultado | MP4 decodificado integralmente sem erro | MP4 decodificado integralmente sem erro |
| Janela até observar conclusão | <= 103.6 s | <= 122.9 s |

As janelas incluem latência de observação/polling e NÃO são tempos exatos de inferência. Load, conditioning, sampling e decode individuais não estão expostos por esta versão do MCP; get_logs apontou arquivo antigo, portanto não foram inventados. Amostras esparsas de VRAM/RAM são observações, não pico garantido. O benchmark harness deve manter campos desconhecidos nulos e registrar método de medição.

H3 exigiu correção de compatibilidade do SaveVideo de codec para format.codec somente na cópia runtime0342 do benchmark. Original preservado. LTX passou com avisos de nós órfãos opcionais e união FLOAT,INT. O LTX usa como âncora um frame do cenário neutro H3, portanto estes dois jobs NÃO constituem A/B de qualidade entre motores. Nenhum recebeu aprovação humana.

Runtime confirmado: ComfyUI 0.34.2, Python 3.11.9, torch 2.14.0+cu130, RTX5090, driver 616.64, allocator cudaMallocAsync. H3 chama optimized_attention, sem patch explícito de attention/compile/cache no grafo; backend efetivo e offload detalhado não medidos. LTX usa os VAEs BF16 e upscaler espacial instalado; nenhuma conversão para FP8 foi aplicada.

REFERENCE preserva os caminhos existentes, incluindo a correção de schema do exporter necessária ao runtime ativo. FAST_SAFE inicialmente é um alias conservador de REFERENCE, sem alegar ganho de velocidade nem promoção automática. EXPERIMENTAL contém recomendações desativadas: Turbo já em disco exige A/B; Sol-Attn/Sol-Engine, caches aproximados e latent upscaler H3 exigem disponibilidade, licença, isolamento e benchmark. Não instalados por esta auditoria.

Antes do LTX, free_memory via MCP pediu liberação do H3 concluído; verificação subsequente confirmou ~32,26 GB de VRAM livre. Nenhum processo foi morto/reiniciado. Dez jobs antigos conhecidos no MCP retornaram prompt_not_found quando consultados individualmente; não foram reenviados/apagados.

Esta etapa produz baseline funcional e limites explícitos de instrumentação. Não qualifica AUTO, não prova superioridade semântica e não habilita HQ latente. Medição por estágio, múltiplas seeds e a bateria B01–B13 continuam como critérios do harness, com status não medido até execução real.
