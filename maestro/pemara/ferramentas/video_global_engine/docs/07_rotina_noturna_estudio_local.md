# Rotina Noturna - Estudio Local Pemara

Data de instalacao: 2026-07-05

## Objetivo

Rodar durante a madrugada testes locais para aproximar o Estudio Pemara do benchmark VEO 3.1:

`E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/output/ritmos_intro_60s_final_fhd.mp4`

O foco nao e gerar 60s completos toda noite. O foco e descobrir, por A/B, quais configuracoes locais conseguem chegar perto do VEO:

- Wan 5B baseline;
- LoRA de estilo em forcas diferentes;
- LoRA pronta de camera/motion;
- LTX;
- Wan A14B High/Low com DRAM/offload em takes aprovados.

## Task Instalada

Nome:

`Pemara Video Studio Local Nightly`

Horario:

`00:31` diariamente

Proxima execucao confirmada apos instalacao:

`2026-07-06 00:31:00`

Modo:

interativo do usuario `admin_remoto`.

## Scripts

Orquestrador:

`E:/Pemara/maestro/pemara/ferramentas/video_global_engine/run_nightly_local_studio.ps1`

Instalador:

`E:/Pemara/maestro/pemara/ferramentas/video_global_engine/install_nightly_local_studio_task.ps1`

Restaurar tasks antigas:

`E:/Pemara/maestro/pemara/ferramentas/video_global_engine/restore_sprunki_gpu_tasks.ps1`

## Janela De GPU

O script so roda dentro de:

`00:31-04:55`

Ele usa lock:

`E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/nightly_local_studio.lock`

Se a fila do Comfy estiver ocupada, ele espera um tempo. Se nao houver tempo suficiente antes do fim da janela, pula a variante.

## Variantes Atuais

Rodada noturna atual:

1. `takes 02 e 04`, LoRA `0.12`, `36` steps.
2. `takes 02 e 04`, LoRA `0.16`, `40` steps.

Motivo:

- o preview com LoRA `0.06` alucinou mais e foi rejeitado como referencia;
- o VEO golden mostra que precisamos de mais acao/camera/energia;
- takes 02 e 04 sao bons testes de rua/camera e objeto/energia.

## Tasks Pausadas Para Nao Disputar GPU

Foram pausadas:

- `Pemara Sprunki LoRA Daily Training`
- `Pemara Sprunki FLUX Weekly Compare`
- `Pemara Sprunki LoRA Krea Weekly Experiment`
- `RitmosIntroTreinoStart1300UntilStop`

Para restaurar depois:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File E:\Pemara\maestro\pemara\ferramentas\video_global_engine\restore_sprunki_gpu_tasks.ps1
```

## Logs E Saidas

Logs:

`E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/logs`

Resumo mais recente:

`E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/logs/nightly_local_studio_latest_summary.json`

Takes:

`E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/takes`

Previews montados:

`E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/intro_ritmos_revolta/output`

## Comandos Uteis

Ver task:

```powershell
schtasks /Query /TN "Pemara Video Studio Local Nightly" /V /FO LIST
```

Dry-run manual:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File E:\Pemara\maestro\pemara\ferramentas\video_global_engine\run_nightly_local_studio.ps1 -Start 00:00 -Stop 23:59 -DryRun
```

Rodar manualmente dentro da janela:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File E:\Pemara\maestro\pemara\ferramentas\video_global_engine\run_nightly_local_studio.ps1
```

## Regra

Enquanto esta rotina estiver ativa, o Estudio Local tem prioridade sobre Sprunki para uso de GPU durante a madrugada.
