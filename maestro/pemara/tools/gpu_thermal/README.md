# RTX 5090: perfil de 500 W

O proprietario escolheu 500 W em 2026-09-04, substituindo a proposta inicial
de 400 W. A placa identificada por UUID termina em `953eb8`; o limite
original preservado em `state/before-cool-profile.json` e 575 W.

- `Set-PemaraGpuCoolProfile.ps1 -Action Apply -InstallAtLogon` aplica o teto
  global de 500 W e persiste no logon. Exige administrador.
- `Set-PemaraGpuCoolProfile.ps1 -Action Restore` restaura o limite original
  e remove apenas as tarefas agendadas deste perfil. Exige administrador.
- Nao altera tensao, clocks configurados ou curva das ventoinhas. Nao e undervolt.
- O teto global afeta tanto renders quanto jogos. Pode reduzir desempenho;
  a reducao de potencia nao corresponde diretamente a mesma reducao de FPS.
  Nenhum parametro de qualidade, steps ou resolucao do video foi reduzido.

## Protecao do projeto R17

`r17_gpu_thermal_guard.py`, nos tools do projeto Cage x Scorpion, exige
limite de no maximo 500 W (tolerancia de leitura de 0,5 W), temperatura
inicial abaixo de 65 C e os manifestos explicitamente despausados.
Durante o render, consulta os sensores a cada 2 s. Aos 85 C, perda de
telemetria ou remocao do limite, solicita cancelamento somente do job
conhecido e pausa novas geracoes. Uma falha do runner tambem cancela seu job.

Isso NAO trava fisicamente a temperatura: ha latencia de consulta e a GPU
ou o ComfyUI podem nao responder, ou concluir um kernel antes de interromper.
O limite de potencia do driver continua sendo a contencao principal.
Esse monitor e especifico do render R17; nao interrompe jogos.

Em 2026-09-04, apos a primeira retomada ter sido cancelada a 80 C,
o proprietario autorizou continuar e informou aceitar 80 C sob carga.
O guard passou a avisar aos 80 C e solicitar cancelamento aos 85 C.
O limite maximo publicado pela NVIDIA para a RTX 5090 e 90 C;
isso nao significa que qualquer falha abaixo dele seja inofensiva ou termica.
Fonte: https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5090/

### Excecao restrita ao take 04 / tentativa 02

O proprietario pediu explicitamente concluir esse take sem os cortes adicionais
a 80/85 C. `r17_t04_a02_finish_once.py` usa 90 C somente nessa execucao,
mantendo o teto de 500 W, sensores, validacao dos hashes e protecoes originais
do hardware. O padrao do guard continua em 85 C; a excecao nao muda outros
projetos, nao permite superar 90 C e nao autoriza takes seguintes.
O recibo de execucao e exclusivo, e o projeto volta a pausado ao terminar.

As quedas anteriores tiveram registro de TDR e leituras de 84-86 C,
mas isso nao prova causa exclusivamente termica. A atualizacao recente do
driver e a alimentacao permanecem hipoteses. A potencia nominal da fonte
nao exclui problemas de cabo, conector ou alimentacao.

O projeto fica pausado, sem retry automatico. Leitura em repouso e testes
simulados do guard nao validam estabilidade em carga: e preciso observar
um teste monitorado antes de retomar o take 04. Nao alterar aprovados.

Fontes: [NVIDIA SMI](https://docs.nvidia.com/deploy/nvidia-smi/index.html),
[Microsoft TDR](https://learn.microsoft.com/en-us/windows-hardware/drivers/display/timeout-detection-and-recovery).
