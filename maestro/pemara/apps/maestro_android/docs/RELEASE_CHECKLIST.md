# Validacao da beta 1.0.0-beta.10

Data: 2026-08-11

## Concluido

- [x] Projeto Android reproduzivel com Gradle Wrapper.
- [x] `testBetaUnitTest` aprovado, incluindo o hostname privado exato, portas autorizadas e dominios parecidos hostis.
- [x] `lintBeta` aprovado com erros e avisos tratados como bloqueantes.
- [x] `assembleBeta` aprovado com encolhimento de recursos e R8.
- [x] APK nao depuravel e pacote beta separado.
- [x] Assinatura APK v2 verificada.
- [x] Manifesto inspecionado: Android 8.1+, target 36, Internet e microfone; a permissao de audio so e pedida depois do toque em **Falar**.
- [x] Trafego em texto claro, conteudo misto e erros TLS bloqueados.
- [x] Upload por seletor/camera e downloads diretos/`blob:` implementados.
- [x] Endpoint publico do Maestro mantido sem alteracao.
- [x] Barra nativa permanente com Maestro, OpenCode, ComfyUI e GPU Qwen.
- [x] OpenCode e ComfyUI carregados somente pelo hostname HTTPS exato do Tailscale.
- [x] Primeiro acesso alinha a senha do OpenCode com a senha atual do Maestro.
- [x] Senha entregue ao configurador por `stdin`, gravada com DPAPI no servidor e Android Keystore no telefone.
- [x] Endpoint de senha unica limita corpo, origem, acao e tentativas; senha nao entra em URL, argumento ou log.
- [x] Credencial lembrada e apagada automaticamente se o OpenCode a recusar.
- [x] A tela inicial mostra se o Qwen esta ativo, onde o OpenCode esta trabalhando e qual fonte confirmou o uso.
- [x] A liberacao exige ociosidade continua confirmada por OpenCode e pelo processo NVIDIA.
- [x] Estado ativo ou indeterminado bloqueia o botao; erro de consulta nunca habilita a acao.
- [x] Controle privado validado no estado real: oito sessoes ativas, diretorio atribuido e liberacao recusada com `409 qwen_active`.
- [x] Interface publica responsiva atual confirmada no endpoint carregado pelo aplicativo.
- [x] Launcher generico substituido pelo mascote oficial Pemara em recursos adaptativo, redondo, por densidade e monocromatico.
- [x] Icone inspecionado nas mascaras quadrada, circular e squircle, sem corte das antenas ou dos fones.
- [x] Navegacao inicial e User-Agent identificados como `1.0.0-beta.10`.
- [x] WebView concede somente `AUDIO_CAPTURE`, apenas ao host exato do Maestro e somente apos a permissao Android.
- [x] Pedidos de camera, origem parecida, recurso misto ou qualquer permissao WebRTC desconhecida continuam negados.
- [x] Negativa recuperavel mostra o motivo e permite tentar novamente sem abandonar o campo.
- [x] Negativa permanente abre a pagina de permissoes do pacote exato e reconcilia o retorno ao aplicativo.
- [x] Cancelar a liberacao preserva **Enviar audio** e libera uma solicitacao WebView pendente.
- [x] Atualizacao invalida o snapshot/cache web antigo sem apagar cookies nem login.
- [x] Estado salvo com mais de cinco minutos nao e restaurado; retorno prolongado recarrega a interface.
- [x] Certificado SHA-256 identico ao da beta.7, permitindo atualizacao no lugar.
- [x] Nenhuma credencial ou chave de producao adicionada ao repositorio.
- [x] APK `versionCode=10`, assinatura v2 e SHA-256 `61319CAC131131DDBD724104E7622C5730E44B7FB00D74FA3AFADCD55FDA654B`.

## Pendente no aparelho

- [ ] Instalar em telefone Android fisico.
- [ ] Entrar e reabrir o app para confirmar persistencia da sessao.
- [ ] Conectar o Tailscale, abrir OpenCode e informar uma vez a senha atual do Maestro.
- [ ] Fechar/reabrir o aplicativo e confirmar entrada automatica no OpenCode.
- [ ] Aprovar ou recusar uma permissao real pela interface movel do OpenCode.
- [ ] Tocar em **GPU Qwen** durante atividade e confirmar que a tarefa/pasta aparecem.
- [ ] Após o Qwen ficar ocioso, confirmar a liberacao e a abertura do ComfyUI.
- [ ] Selecionar uma foto da galeria e capturar uma foto pela camera.
- [ ] Tocar em **Falar**, autorizar o microfone, gravar um prompt e confirmar a insercao do texto.
- [ ] Negar o microfone e confirmar que **Enviar audio** continua funcional.
- [ ] Negar novamente, tocar em **Abrir configuracoes**, liberar Microfone e confirmar a retomada ao voltar.
- [ ] Reproduzir um video da Biblioteca.
- [ ] Salvar um download direto e um download `blob:`.
- [ ] Alternar Wi-Fi/dados e testar **Tentar novamente**.

Esses itens nao foram simulados porque `adb devices` nao encontrou aparelho e o SDK local nao possui uma imagem de sistema para emulador.

## Producao futura

- [ ] Definir a conta Google Play da Pemara.
- [ ] Criar/importar a chave oficial e manter backup offline.
- [ ] Gerar AAB de release sem `applicationIdSuffix`.
- [ ] Publicar primeiro em teste interno e concluir a ficha de seguranca de dados.
