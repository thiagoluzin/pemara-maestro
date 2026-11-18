# PEMARA Pika Flex experimental

Importe um dos três arquivos JSON sem `.api` no ComfyUI, em `PEMARA Pika Flex`. O arquivo `.api.json` correspondente é usado na validação/envio pelo MCP. Os templates originais estão preservados em `E:/Pemara/work/pika_flex_update_20261101/official`.

- T2V: texto para vídeo, 832×480, exemplo de animação original.
- FL2VA: primeiro e último quadro, exemplo oficial 864×1536.
- REF2VA: referências de sujeito/cena, exemplo oficial 1344×768.

Os três usam 124 quadros, 24 FPS, seis passos LCM, sigmas oficiais, CFG 1, LoRA 1.0 e áudio nativo. SageAttention e a proteção de quatro grupos estão conectados. Spectrum está desligado somente neste experimento, com a autorização expressa do proprietário. O Master do Maestro continua Sage + Spectrum.

Declare corretamente o tipo no nó PemaraDLSS5ContentPolicy antes de gerar outro conteúdo. Os exemplos FL2VA/REF2VA são mixed. Nenhum DLSS é aplicado ao vídeo ou aos seus quadros. Os assets de exemplo estão na entrada do ComfyUI, sem sobrescrever arquivos existentes.

Validação MCP passou nos três modos. Somente T2V teve piloto real de GPU: `da1d7f41-836e-497d-95a0-eb4a3366ecf2`. O vídeo decodificou integralmente, com áudio. A revisão visual foi por amostras; fala, qualidade temporal integral e aprovação artística ainda dependem de revisão humana. Não representa benchmark comparativo nem qualificação GPU dos outros dois modos.

Fontes: https://docs.comfy.org/tutorials/video/pika/pika-h3-flex e https://huggingface.co/Comfy-Org/MiniMax-H3
