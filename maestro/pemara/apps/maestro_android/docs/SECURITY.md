# Seguranca do aplicativo Android

## Fronteira de confianca

O aplicativo aceita navegacao interna somente por HTTPS e somente para estes hosts exatos:

- `maestro.pemaratech.com.br`
- `comfy.pemaratech.com.br`
- `sprunki.pemaratech.com.br`
- `perplexica.pemaratech.com.br`
- `pc-geral-thiago-1.tail14cf8c.ts.net`, apenas nas portas HTTPS `443`, `8443` e `10000`

Comparacoes usam o host analisado da URI, sem correspondencia por sufixo. HTTP, portas inesperadas, credenciais na URL, esquemas executaveis e dominios parecidos sao bloqueados. A porta interna `4096` e a porta de controle `10443` nao podem ser abertas pela navegacao do WebView. Links HTTPS externos abrem fora do WebView.

## Sessao e dados

- O APK nao contem senha, cookie ou token do Studio. O nome de servico `opencode`
  nao e uma credencial secreta.
- O login acontece no gateway oficial.
- O cookie `HttpOnly`, `Secure` e `SameSite=Strict` e persistido pelo armazenamento privado do WebView.
- O OpenCode usa Basic Auth no endpoint privado do Tailscale. O usuario e fixo em
  `opencode`; a senha nao e embutida no APK.
- No primeiro uso, a senha unica e cifrada em AES-GCM por uma chave nao exportavel
  do Android Keystore. Backup e transferencia dos dados do aplicativo estao
  desativados.
- Se o servidor recusar a credencial lembrada, o aplicativo apaga o valor cifrado e
  solicita a senha atual novamente.
- Backup e transferencia dos dados privados do aplicativo estao desativados.
- Depuracao de conteudo WebView fica desativada inclusive na beta entregue.
- O app nao registra URLs autenticadas, cookies ou conteudo baixado.

## WebView

- trafego HTTP em texto claro e conteudo misto sao bloqueados;
- acesso a caminhos `file://` e acesso universal por arquivo ficam desativados;
- Safe Browsing permanece ativo;
- erros de certificado TLS sao sempre cancelados;
- geolocalizacao, camera WebRTC e recursos WebView desconhecidos sao negados;
- `AUDIO_CAPTURE` e aceito somente no host exato `maestro.pemaratech.com.br`,
  sem recursos mistos, depois da autorizacao `RECORD_AUDIO` do Android;
- nao existe ponte JavaScript generica para executar comandos nativos.

A ponte JavaScript limitada de download aceita apenas blocos Base64 para um arquivo que o proprio usuario acabou de escolher. Ela so e iniciada no host principal do Maestro, limita cada bloco, limita o total a 8 GiB e nao recebe caminhos do sistema.

## Senha unica

O primeiro acesso envia a senha informada somente ao endpoint HTTPS privado e fixo
`/api/actions/unify-opencode-password`, na porta `10443` do Tailscale. O servidor:

- exige cabecalho de acao fixo, JSON e corpo de no maximo 4 KiB;
- limita a cinco tentativas em quinze minutos;
- valida a senha atual pelo login local do Maestro em `127.0.0.1`;
- entrega a senha ao PowerShell por `stdin` codificado, nunca por argumento ou log;
- grava o cofre do OpenCode com DPAPI no usuario Windows atual;
- mantem backup DPAPI e restaura a credencial anterior se o reinicio falhar;
- reinicia somente o OpenCode e valida a autenticacao antes de responder sucesso.

A porta `10443` nao e navegavel no WebView. Ela e usada apenas pelas chamadas nativas
fixas de senha unica e controle da GPU.

## Controle da GPU

O botao **GPU Qwen** nao aceita texto, caminho, URL ou comando fornecido pela
pagina. Antes de exibir a confirmacao, o codigo nativo consulta `GET /api/status`
no hostname privado fixo. O servidor correlaciona as sessoes `busy/retry` do
OpenCode por diretorio com o processo `llama-server` na NVIDIA. Somente o estado
`loaded_idle`, mantido por uma janela continua de confirmacao, autoriza
`POST /api/actions/release-qwen`.

Atividade, falha de sensor, falha de autenticacao ou resposta incompleta bloqueiam
a operacao. O servidor repete a validacao imediatamente antes do comando fixo,
recusa redirecionamentos e nunca aceita um nome de modelo ou comando vindo do
telefone. Assim, um estado incerto nao e convertido em permissao para parar o Qwen.

## Arquivos

- Uploads usam o seletor do Android e permissoes temporarias de URI.
- A camera externa grava somente no cache privado compartilhado por `FileProvider`.
- Downloads HTTPS validam novamente o host em cada redirecionamento.
- O aplicativo nao usa `DownloadManager` nem pede acesso amplo ao armazenamento.
- O destino de cada download e escolhido explicitamente pelo usuario por Storage Access Framework.

## Assinatura

`MaestroStudio-1.0.0-beta.10.apk` e uma build nao depuravel, otimizada e assinada com certificado de desenvolvimento para sideload. Antes de Play Store ou distribuicao publica definitiva, criar ou importar a chave oficial da Pemara, guarda-la fora do repositorio e gerar um Android App Bundle de producao.
