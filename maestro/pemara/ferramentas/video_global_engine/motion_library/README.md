# Biblioteca Pemara de movimentos

Esta biblioteca cataloga **movimento**, não aparência nem identidade. Um driver aprovado pode ser aplicado a personagens diferentes quando a ação, o enquadramento e a licença forem compatíveis.

O arquivo `registry.json` é o índice legível pelo Maestro. Ele aponta para os ativos preservados em seus projetos sem duplicar vídeos grandes desnecessariamente.

## Estrutura planejada

```text
motion_library/
  apresentacao/
  caminhada/
  reacoes/
  musica/
  combate/
  personagens/
  stock_licenciado/
  rejected/
```

Crie as pastas conforme os primeiros drivers forem registrados. Material rejeitado fica isolado e nunca deve ser reutilizado automaticamente.

## Nome dos arquivos

```text
driver_<acao>_<origem>_vNN_<frames>f_720p30.mp4
```

Exemplo:

```text
driver_apresentacao_usuario_v01_149f_720p30.mp4
```

Cada MP4 normalizado deve ter um JSON com o mesmo nome-base contendo:

- versão do schema e status;
- fonte, autoria, proveniência e licença/permissão;
- janela usada, resolução, FPS e número de quadros;
- descrição dos beats da ação;
- resultado do QC DWPose para corpo e mãos;
- política de rosto (`disabled`, por padrão);
- aprovação, responsável e data;
- renders em que o driver foi utilizado.

## Estados

```text
raw -> normalized -> pose_qc_passed -> user_approved -> used_in_render
```

Um arquivo com falha segue para `rejected` acompanhado do motivo. Não promova automaticamente um driver apenas porque o detector conseguiu abrir o vídeo.

## Privacidade e licença

- Gravações do usuário permanecem locais, salvo autorização explícita para envio.
- Vídeos externos exigem URL de origem e prova de licença compatível.
- Nunca use rosto, voz ou identidade do ator quando o objetivo for somente capturar movimento.

## Primeiro caso validado

O driver de apresentação do projeto Judo Mirassol foi validado em 2026-07-18:

- bruto: `E:/judo_mirassol/references/motion_drivers/WhatsApp Video 2026-07-18 at 17.13.55 (1).mp4`
- normalizado: `E:/judo_mirassol/references/motion_drivers/driver_sensei_usuario_v1_149f_720p30.mp4`
- pose: `E:/judo_mirassol/references/motion_drivers/driver_sensei_usuario_v1_dwpose.mp4`

O acervo do projeto pode permanecer junto ao projeto; esta biblioteca funciona como índice e padrão global até a promoção de um driver para reutilização geral.
