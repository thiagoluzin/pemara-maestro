## DLSS 5 integral obrigatorio — ordem do proprietario, 2026-10-10

DLSS 5 integral e obrigatorio em toda nova ancora, foto-base, imagem, take e acabamento de video, incluindo pessoas, atores, personagens, criaturas e cenario. Vale para live_action, mixed e animation. Sem mascara de exclusao de sujeitos e com auto_mask desligado. Esta ordem substitui a restricao de DLSS somente no cenario de 2026-10-09.

Live action/mixed: Lanczos + NVENC, sem SeedVR2 nem restauracao neural espacial substituta; acabamento com RIFE 4.25 em 60 FPS exatos e DLSS 5 integral. Animation permite SeedVR2 e recebe DLSS integral. Declarar content_kind; unknown ou conflito bloqueia. Parametros integrais: Natural, escala NR 1x, intensidade 1, estrutura 1, pele 1, detalhe/composicao 1, tom 0, cor 0, auto_mask false.

Preservar fonte anterior, alfa, geometria, duracao, som nativo, historico, aprovados/rejeitados e revisao humana. Recibo/hash e execucao NR real obrigatorios; falha bloqueia entrega sem fallback. Copiar arquivo tratado nao autoriza NR recursivo. Esta mudanca nao reabre nem rerenderiza entregas antigas. Flow causal continua obrigatorio nas juncoes entre estados diferentes.

Contrato: E:/Pemara/maestro/pemara/services/studio/dlss5_content_policy.py e upscaling_required.py. Referencia canonica: E:/Pemara/.agents/skills/pemara-video-production-lead/references/dlss5-full-frame-required.md.

# Upscaling obrigatório — receita aprovada em 06/10/2026

**Fonte nativa aprovada → SeedVR2 3B → RIFE 4.25 exato 60 FPS → DLSS 5 Natural → áudio existente preservado → QC → novo candidato para revisão.**

O proprietário escolheu essa combinação como a melhor dos comparativos RE1. O artefato aprovado tem 1080x1920, 900 quadros em 15 segundos e Foley preservado. A aprovação desse arquivo não aprova novas cenas ou novas resoluções.

Os arquivos `upscaling_obrigatorio_*.api.json` são workflows completos de pós-processamento para ComfyUI. A entrada de exemplo é `RE1_NATIVE24_FOLEY.mp4`; o worker do Maestro troca a entrada, calcula a geometria e reserva um nome novo. `seedvr2_stage_template.json` é somente a base histórica da etapa de restauração, não o fluxo completo a executar.

| Perfil | Paisagem | Vertical | Pixels relativos ao FHD |
| --- | --- | --- | --- |
| 1080p / FHD | 1920x1080 | 1080x1920 | 1x |
| 1440p / QHD | 2560x1440 | 1440x2560 | 1,78x |
| 4K / UHD | 3840x2160 | 2160x3840 | 4x |

Para subir de resolução, restaurar diretamente a fonte nativa para o tamanho de conteúdo do destino. Não ampliar o MP4 FHD já comprimido para produzir o master 4K. No RE1 (proporção 4:7), o conteúdo fica em 1080x1890, 1440x2520 ou 2160x3780, com barras centradas de 15, 20 ou 30 pixels no topo/base. A imagem não é recortada nem esticada.

As etapas e modelos permanecem os mesmos: SeedVR2 **3B int8**, um passo Euler/simple, CFG 1, seed 20261006, correção LAB, chunks temporais de 17 quadros com overlap latente 1; VAE tiled 512/overlap 128/temporal 16/overlap 4; RIFE **4.25** com avaliação de cada posição j/60; DLSS Natural **1x** com os parâmetros aprovados; NVENC H.264 p7/CQ15. O DLSS opera no tamanho restaurado e não faz uma segunda ampliação. Aumentar resolução exige mais memória/tempo/espaço; esses custos não escalam obrigatoriamente de forma linear. A quantidade de detalhe recuperável depende da fonte.

O RIFE calcula a fração real entre os quadros de origem; pares detectados como corte pela diferença média RGB > 0,35 usam o quadro mais próximo para evitar mistura entre cenas. O limiar é uma proteção heurística, não prova de que todo corte ou movimento foi identificado. A duração deve corresponder a um número inteiro de quadros a 60 FPS; caso contrário, a operação bloqueia para uma decisão editorial explícita. Não cortar ou alongar silenciosamente.

O áudio é copiado com o FFmpeg do runtime DLSS isolado, preservando o payload e o PCM no intervalo do vídeo. Não gerar Foley novo implicitamente. Fonte silenciosa permanece silenciosa. Limites atuais: SDR 8-bit, CFR 24..60 FPS, duração alinhada a 1/60 s e até uma faixa de áudio. HDR, múltiplas faixas e cadência variável exigem qualificação própria.

Integração: `services/studio/upscaling_required.py` é o contrato; o botão de upscale usa `tools/postprocess_required_upscale.py`; o nó final `PemaraUpscaleRequiredSave` executa o acabamento inteiro dentro do worker serial do ComfyUI. Perfis antigos continuam em disco para histórico, mas novos jobs não os selecionam. A montagem final exige recibos válidos da cadeia completa nos takes aprovados e herda o vídeo por cópia de bitstream, evitando repetir os passes neurais. Prévias nativas de geração preservam o motor, tamanho e gate de aprovação da fonte.

Quando uma prévia recebeu DLSS obrigatório, o worker recupera a cópia anterior ao DLSS, verifica hash, geometria, cadência e áudio e usa essa fonte para restaurar. Fonte retida ausente ou incompatível bloqueia; não aplicar SeedVR2 recursivamente a uma saída final por conveniência.

Verificação de implantação: oito testes do contrato, oito testes do DLSS e checks de integração de cache, perfil, resolução e montagem. Os seis grafos passaram na validação do runtime pelo MCP. Dois testes reais FHD de 1 segundo passaram: um silencioso, outro com áudio; ambos têm 60 quadros a 60 FPS e recibos completos. QHD e UHD estão preparados e validados estruturalmente, sem render ou aprovação visual nessas resoluções ainda.

Fontes técnicas consultadas: [SeedVR oficial](https://github.com/ByteDance-Seed/SeedVR), [Practical-RIFE oficial](https://github.com/hzwer/Practical-RIFE). Codex deve validar/enviar/obter resultados exclusivamente pelo MCP `comfyui-local`; o CLI de cliente direto é reservado ao backend autônomo do Maestro.
