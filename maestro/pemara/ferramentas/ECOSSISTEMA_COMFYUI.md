# Ecossistema ComfyUI Pemara

## Objetivo
Transformar o ComfyUI principal em um servico unico para:

- imagens de Sprunki e personagens;
- videos e abertura animada em `lora_videos`;
- propaganda Pemara com fotos reais de produto;
- treinos LoRA com janelas controladas.

## Regra central
O ComfyUI principal em `E:\Pemara\maestro\pemara\ferramentas\ComfyUI` deve ser o nucleo.

Pipelines consumidores devem falar com `http://127.0.0.1:8188` pela API. Evitar subir outro ComfyUI na mesma porta, porque isso causa queda, disputa de processo e confunde watchdogs.

O ComfyUI nunca deve ser iniciado com `--listen 0.0.0.0`. Se a API responder, mas a porta estiver exposta em `0.0.0.0:8188`, o estado deve ser tratado como falha e o Radar/watchdog deve reiniciar.

## Componentes

| Area | Caminho | Papel |
| --- | --- | --- |
| ComfyUI principal | `ComfyUI\` | API unica de geracao |
| Sprunki | `gerador_sprunki\` | imagens, samples, LoRA Flux |
| Videos | `ComfyUI\lora_videos\` | Wan I2V, LoRA Ritmos, repixel, montagem |
| Marketing | `E:\Pemara\marketing_social` | cards com foto real + design |
| Treino Wan LoRA | `ComfyUI\lora_videos\wan_lora_trainer` | treino Ritmos pixel |

## Watchdogs e rotinas

| Tarefa | Funcao | Status desejado |
| --- | --- | --- |
| `Pemara ComfyUI Watchdog` | Mantem ComfyUI principal online | a cada 1 min |
| `Pemara_Radar` | Recupera Maestro, loja, Sprunki, tunel e ComfyUI exposto/offline | S4U / Highest |
| `Pemara Marketing Fotos Reais` | Busca fotos reais e gera cards | diario 06:20 |
| `RitmosTreinoStart` | inicia treino LoRA de video | seg-sex 07:00 |
| `RitmosTreinoStop` | para treino LoRA de video | seg-sex 11:30 |
| `RitmosTreinoWatchdog` | revalida treino a cada 5 min | pausado sem `training_enabled.flag` |
| `RitmosTreinoStartUser/StopUser` | fallback sem SYSTEM | seg-sex 07:00/11:30 |

## Lora Videos

O script `ritmos_animacao_kit\kit\gerar.py` agora respeita:

- `COMFY_SERVER`: URL da API, padrao `http://127.0.0.1:8188`;
- `COMFY_ROOT`: pasta do ComfyUI usado para `input` e `output`.

Novo launcher recomendado:

```powershell
cd E:\Pemara\maestro\pemara\ferramentas\ComfyUI\lora_videos\ritmos_animacao_kit\kit
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_video_on_main_comfy.ps1 -Piloto
```

Para lote completo:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_video_on_main_comfy.ps1
```

O batch legado `2_gerar_tudo.bat` ainda existe, mas deve ser considerado fallback, porque sobe o ComfyUI do kit e encerra o processo no final.

## Direcao do LoRA v4

Base recomendada pelo resumo:

- voltar para single-frame;
- rank 32;
- learning rate `1e-5`;
- 12k steps;
- captions focadas em pixel art duro;
- dataset maior com keyframes + frames extraidos dos clips;
- testar LoRA v2 no ComfyUI com strength `0.3-0.4`.

O watchdog de treino agora fica travado por seguranca ate existir:

```text
E:\Pemara\maestro\pemara\ferramentas\ComfyUI\lora_videos\wan_lora_trainer\training_enabled.flag
```

Crie essa flag somente depois de trocar o config divergente v3 por uma configuracao v4 validada.

## Status rapido

Use:

```powershell
cd E:\Pemara\maestro\pemara\ferramentas
powershell -NoProfile -ExecutionPolicy Bypass -File .\check_comfy_ecosystem.ps1
```
