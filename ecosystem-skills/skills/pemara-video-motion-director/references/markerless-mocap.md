# Markerless Mocap: DWPose + Wan Animate

Use esta rota quando a atuação precisar ser controlada e o prompt-only I2V resultar em foto viva, gesto repetitivo, mão instável, balanço corporal ou timing incorreto.

## Princípio

- imagem aprovada = identidade, roupa, rosto e marca;
- vídeo driver = corpo, mãos e timing;
- câmera/parallax = passe separado após aprovar a atuação;
- rosto do driver = desativado, salvo autorização explícita.

O usuário pode ser o ator para qualquer personagem. Isso é captura de movimento 2D sem marcadores; não é cópia da identidade do ator.

## Gate obrigatório

1. Grave uma ação de 3–6 s, câmera estável, mãos e articulações visíveis.
2. Normalize para 1280x720, 30 FPS e preferencialmente `4n+1` quadros (149 ou 181).
3. Rode DWPose com corpo+mãos ligados e rosto desligado.
4. Gere MP4 de pose e contact sheet densa.
5. Obtenha aprovação do usuário antes de iniciar Wan Animate.

Cabeça cortada só passa quando rosto está desligado e pescoço, ombros, braços e mãos permanecem rastreáveis. Nunca use esse driver para expressão facial.

## Produção

- Wan2.2 Animate 14B BF16 nativo, sem quantização.
- Pose strength inicial `1.0`.
- Relight LoRA somente quando necessário.
- Saída 1280x720 a 30 FPS; nunca abaixo de 24 FPS e nunca a 16 FPS.
- Preserve boca, rosto, uniforme, texto e logotipos da referência.
- Uma renderização de produção + no máximo uma correção dirigida.

Se o mesmo defeito estrutural persistir, troque driver/controle/modelo ou migre para rig/3D. Não faça loop de seed.

## Limite físico

DWPose fornece articulações 2D visíveis. Ele não garante profundidade, peso, contato ou biomecânica. Judô, luta, quedas e interação entre corpos podem exigir referência especializada ou 3D.

## Componentes locais

- Modelo: `E:/Pemara/maestro/pemara/ferramentas/ComfyUI/models/diffusion_models/wan2.2_animate_14B_bf16.safetensors`
- Relight LoRA: `E:/Pemara/maestro/pemara/ferramentas/ComfyUI/models/loras/wan2.2_animate_14B_relight_lora_bf16.safetensors`
- Executor: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/Ritmos da Revolta/tools/run_wan_animate_move.py`
- Guia completo: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/docs/11_markerless_motion_capture_wan_animate.md`
- ADR: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/docs/decisions/ADR-001-markerless-motion-capture.md`
- Biblioteca: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/motion_library/README.md`
- Registro para o Maestro: `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/motion_library/registry.json`
