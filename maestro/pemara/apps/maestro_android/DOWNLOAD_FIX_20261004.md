# Android beta.11: integridade de downloads

Relato do proprietario: Android salva video que termina antes da hora; o mesmo
video baixado no navegador fica completo. Sem arquivo defeituoso nem log do
aparelho, a causa individual ainda nao pode ser atribuida a rede, encerramento
do app ou resposta parcial.

Falhas confirmadas na beta.10: SecureDownloader descartava Content-Length,
aceitava qualquer 2xx (incluindo 206), copiava ate EOF e anunciava sucesso sem
contar bytes. BlobDownloadBridge tambem concluia sem tamanho esperado. Ambos
gravavam diretamente no destino usando modo w, deixando uma transferencia
incompleta no arquivo escolhido. DownloadListener recebia contentLength e o
MainActivity o descartava.

## Correcao entregue

- HTTP exige resposta 200 completa, sem Content-Range, solicita encoding identity
  e valida tamanho recebido contra Content-Length (ou tamanho do listener quando
  o header falta). Divergencias, tamanho desconhecido e mais de 8 GiB falham.
- Blob informa tamanho antes dos chunks e exige contagem exata na conclusao.
  O script WebView interrompe se a bridge recusar um chunk.
- Ambos recebem em arquivo temporario privado; somente um corpo completo e
  copiado ao destino em modo wt. Conexoes sao fechadas e temporarios do download
  sao descartados. Um segundo download espera o atual terminar.
- Mensagens distinguem arquivo completo de download nao concluido.

## Evidencia

- testBetaUnitTest: 33 testes, zero falhas/erros; 15 novos de integridade.
- Teste com servidor TCP real anuncia 100000 bytes, envia 1024 e fecha: falha
  detectada; nenhum byte chega ao destino simulado.
- Copia de mais de 3 MiB preserva SHA-256.
- Script real extraido do MainActivity: 4 cenarios passaram (blob com header,
  sem header, corpo curto e chunk recusado).
- lintBeta: zero issues. assembleBeta/R8: sucesso.
- APK pacote com.pemaratech.maestrostudio.beta, versionCode 11,
  versionName 1.0.0-beta.11-sideload, minSdk 27, targetSdk 36.
- apksigner verifica beta.10 e beta.11 com o mesmo certificado SHA-256:
  294d81aabaeb670628dfd58ec87e615be81b4d7ed95b65e16cdeb5e276bd5f0e.
- APK 1490251 bytes, SHA-256:
  dd6249bff91c8c77a29c629d74dfd006a63cebf606f1b3cf5f7f2da42609d457.
- GET local e publico (User-Agent de navegador) retornam HTTP 200, tamanho
  correto e SHA-256 identico. URL:
  https://maestro.pemaratech.com.br/assets/downloads/MaestroStudio-1.0.0-beta.11.apk
- Nenhum Android conectado ao adb; nenhuma instalacao no telefone foi executada.
  Seletor SAF e reproducao no aparelho continuam pendentes de teste humano.

## Limites e recuperacao

Esta correcao nao implementa retomada nem foreground service. Manter o app
aberto durante o download. Encerramento do processo ou falha do provedor SAF
durante a copia final ainda podem deixar um documento vazio/incompleto; o app
nao garante atomicidade de provedores externos. Espaco para staging e destino
e necessario. Arquivos ja baixados incorretamente precisam ser baixados de novo.
Nao houve geracao, alteracao de video nem uso de GPU.

Originais da fonte preservados em backups/download_integrity_20261004_070950;
APK beta.10 preservado em dist. Atualizacao pelo mesmo pacote/certificado
permite instalar sobre a beta anterior; downgrade pode depender do Android.

## Compilacao nesta maquina

OpenJDK 21.0.8 instalado em C:/Program Files/Android/openjdk/jdk-21.0.8.
O socket AF_UNIX do Java falhou com Invalid argument: connect. Para esta
compilacao apenas, JAVA_TOOL_OPTIONS apontou jdk.net.unixdomain.tmpdir para o
diretorio inexistente build/no-unix-socket-dir, permitindo o fallback TCP
implementado pelo Java. Nao alteramos Java global, Gradle global ou rede.
