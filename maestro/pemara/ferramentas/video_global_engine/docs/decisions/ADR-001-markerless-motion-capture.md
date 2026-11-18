# ADR-001: Captura de movimento sem marcadores para atuação controlada

- Status: Aceita
- Data: 2026-07-18
- Escopo: gerador local de vídeos Pemara e integração futura ao Maestro

## Contexto

Os testes de image-to-video dirigidos apenas por prompt entregaram boa aparência no quadro inicial, mas falharam repetidamente na atuação: personagem com comportamento de “foto viva”, gesto de guarda de trânsito, balanço corporal artificial, mãos deformadas, movimento de câmera confundido com movimento do ator e variações de identidade. Uma renderização FP16/BF16 nativa de 81 quadros em 720p chegou a consumir aproximadamente 31 minutos e 51 segundos, tornando a repetição por troca de seed cara e pouco produtiva.

Em 2026-07-18, um vídeo gravado pelo próprio usuário foi normalizado e analisado com DWPose. Corpo, braços e mãos foram rastreados nos 149 quadros úteis. O ensaio provou que o usuário pode funcionar como ator de movimento para um personagem diferente, sem transferir sua identidade.

## Decisão

Para atuação humana ou humanoide controlada, o caminho padrão será:

1. gravar ou selecionar um vídeo de movimento com origem e licença conhecidas;
2. normalizar resolução, FPS e janela temporal com FFmpeg;
3. extrair e revisar corpo e mãos com DWPose, mantendo o rosto desativado por padrão;
4. obter aprovação do vídeo normalizado e da prévia de pose antes de usar a GPU;
5. transferir o movimento para a imagem aprovada com Wan2.2 Animate BF16;
6. preservar boca, rosto, uniforme, logotipos e textos da imagem de identidade;
7. fazer QC de identidade, anatomia, ritmo, congelamentos e FPS;
8. somente depois de aprovar a atuação, adicionar câmera, parallax, montagem e acabamento.

Identidade, movimento, rosto e ambiente/câmera são controles separados. Uma única geração não deve ser encarregada de inventar simultaneamente atuação, movimento de câmera e marca gráfica.

O orçamento padrão é de uma renderização de produção e, no máximo, uma correção dirigida. Se o defeito estrutural permanecer, muda-se o controle, o modelo ou a rota para 3D. Não se repete indefinidamente seed e prompt.

## Alternativas consideradas

- **I2V apenas por prompt:** rejeitado para atuação precisa. Continua válido para ambiente, partículas e movimentos não coreografados.
- **Trocar seed/modelo repetidamente:** rejeitado por custo e falta de controle causal.
- **Blender/3D:** alternativa determinística para profundidade, contato, biomecânica e câmera, porém com preparação maior.
- **Vídeo de banco licenciado:** aceito como driver quando origem e licença forem registradas.
- **O próprio usuário como ator:** aceito e recomendado quando o gesto necessário puder ser gravado com segurança.

## Limitações

O método é mocap 2D sem marcadores. Ele controla silhueta e articulações visíveis, mas não reconstrói com exatidão profundidade, equilíbrio, peso, contato ou física entre corpos. Golpes de judô, luta, quedas e interação física exigem referência especializada e podem precisar de rig/3D, biomecânica ou controle de contato adicional.

Cabeça cortada pode ser aceita apenas quando o rosto do driver estiver desativado e a auditoria DWPose comprovar pescoço, ombros, braços e mãos utilizáveis. Esse material nunca será usado para transferência de expressão facial.

## Componentes locais confirmados

- Wan2.2 Animate 14B BF16: `E:/Pemara/maestro/pemara/ferramentas/ComfyUI/models/diffusion_models/wan2.2_animate_14B_bf16.safetensors` (aprox. 32,18 GB)
- LoRA de relight: `E:/Pemara/maestro/pemara/ferramentas/ComfyUI/models/loras/wan2.2_animate_14B_relight_lora_bf16.safetensors` (aprox. 1,34 GB)
- DWPose/YOLOX: nodes instalados no ComfyUI
- Executor local: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/Ritmos da Revolta/tools/run_wan_animate_move.py`

## Evidências do primeiro caso aprovado

- Driver bruto: `E:/judo_mirassol/references/motion_drivers/WhatsApp Video 2026-07-18 at 17.13.55 (1).mp4`
- Driver normalizado: `E:/judo_mirassol/references/motion_drivers/driver_sensei_usuario_v1_149f_720p30.mp4`
- Prévia DWPose: `E:/judo_mirassol/references/motion_drivers/driver_sensei_usuario_v1_dwpose.mp4`
- Metadados: `E:/judo_mirassol/references/motion_drivers/driver_sensei_usuario_v1_149f_720p30.json`
- Prompt ID do ensaio no ComfyUI: `8dce0b28-01d6-4f57-983f-e4cf1ee952b0`

## Consequências

O usuário passa a poder atuar localmente para personagens diferentes, formando uma biblioteca reutilizável de movimentos. Isso reduz tentativas cegas na GPU, melhora a direção e abre caminho para dança, apresentação, reação, caminhada, performance musical e cenas narrativas controladas.
