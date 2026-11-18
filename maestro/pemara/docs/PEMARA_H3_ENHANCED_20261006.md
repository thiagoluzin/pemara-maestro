# PEMARA H3 Enhanced — direção de 2026-10-06

Face Refine permanece removido por decisão do proprietário. Não detectar,
recortar, regenerar e colar o rosto após a geração. `h3_face_refine.py` mantém
apenas a compatibilidade que retira nós antigos e a proteção independente do Sage.

Fluxo aprovado pelo proprietário em 2026-10-06: âncora-mãe + referências + direção de movimento/continuidade →
H3 com Sage + Spectrum → VAE → QC técnico + aprovação da fonte →
SeedVR2 3B → RIFE 4.25 exato 60 FPS → DLSS 5 Natural → áudio existente → candidato final.

- A âncora-mãe mantém rosto, corpo, roupa, materiais e iluminação de referência.
- Referências frontal, 3/4 e corpo inteiro devem entrar pelo condicionamento
  compatível do H3; não assumir que FL2VA e Ref2VA aceitam entradas idênticas.
- Movimento, física, atuação e câmera são definidos antes da geração.
- O último frame aprovado ajuda pose e movimento; não substitui a referência original.
  A aprovação do vídeo não aprova automaticamente um frame como nova âncora canônica.
- Preferir os checkpoints pruned int8 qualificados; não migrar para full automaticamente.
- VAE int8 e tiled decode dependem da combinação qualificada; não mudar grafos antigos.
- Continuação mantém referências e estado entre segmentos. Target-Band/Flow-Aligned,
  RefMods e Motion LoRAs ficam opcionais e precisam demonstrar benefício na cena.
- QC deve examinar identidade, roupa, acessórios, mãos, flicker, brilho e junções.
  Esta lista é um critério desejado, não comprovação de que cada detector já existe.
- QC técnico não substitui aprovação artística. Acabamento e exportação seguem os
  contratos obrigatórios; Foley novo exige direção própria, fonte silenciosa continua silenciosa.

A inspeção e 29 testes de remoção, aceleração e contrato H3 confirmaram o comportamento atual de Face Refine.
Nenhum render, novo checkpoint ou mudança de qualidade foi executado nesta revisão.

A atualização aprovada também corrige o catálogo do Maestro para VAE int8 e acabamento SeedVR2 3B + RIFE 4.25 exact60 + DLSS 5, preservando motores e grafos históricos.
