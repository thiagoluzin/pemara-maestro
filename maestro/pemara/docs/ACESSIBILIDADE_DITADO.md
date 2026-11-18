# Ditado acessivel no Maestro

O Maestro aceita voz nas caixas de prompt de imagem, prompt e negativa de
video, orientacoes do editor e justificativas de recusa.

## Como usar

1. Pressione **Falar** ao lado da caixa desejada e permita o microfone.
2. Dite por ate 120 segundos e pressione **Parar e transcrever**.
3. Revise o texto inserido no ponto do cursor antes de enviar a tarefa.
4. Se o navegador bloquear o microfone, use **Enviar audio** como alternativa.

## Privacidade e limites

- A transcricao usa Faster Whisper local em CPU/int8, sem enviar a gravacao
  para servicos de nuvem e sem competir pela GPU de geracao.
- O arquivo temporario e descartado assim que a transcricao termina.
- Cada gravacao pode ter ate 120 segundos e 16 MiB.
- O endpoint exige a mesma sessao autenticada do Maestro e aceita apenas
  formatos de audio/video explicitamente permitidos.

## Celular Android

O aplicativo beta pede `RECORD_AUDIO` somente quando o usuario inicia o
ditado. A WebView libera captura de audio exclusivamente para a origem HTTPS
oficial do Maestro; outras origens ou recursos sao recusados.
