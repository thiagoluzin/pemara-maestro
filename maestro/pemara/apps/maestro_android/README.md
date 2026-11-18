# Maestro Studio para Android

Aplicativo Android do Maestro Studio Pemara. Ele abre a interface publica oficial em uma camada nativa segura e acrescenta os recursos necessarios no celular sem duplicar o backend.

## APK pronto

- Arquivo: `dist/MaestroStudio-1.0.0-beta.11.apk`
- Pacote: `com.pemaratech.maestrostudio.beta`
- Versao: `1.0.0-beta.11-sideload`
- Android minimo: 8.1 (API 27)
- Alvo: Android 16 (API 36)
- SHA-256: `DD6249BFF91C8C77A29C629D74DFD006A63CEBF606F1B3CF5F7F2DA42609D457`

Esta beta e assinada para instalacao direta, mas nao usa a futura chave oficial da Play Store. A versao publica definitiva deve receber a chave de producao da Pemara.

## Como instalar

### Direto no telefone

1. Copie `dist/MaestroStudio-1.0.0-beta.11.apk` para o Android.
2. Abra o arquivo no telefone.
3. Se o Android solicitar, permita a instalacao desta fonte.
4. Abra **Maestro Studio** e entre com o mesmo login do endereco publico.

Para usar os controles privados, conecte o Tailscale no telefone com a mesma tailnet
desta maquina. A barra inferior do aplicativo oferece:

- **Maestro**: retorna ao Studio principal;
- **OpenCode**: abre o agente Qwen desta RTX 5090 dentro do aplicativo;
- **ComfyUI**: abre a interface privada do ComfyUI dentro do aplicativo;
- **GPU Qwen**: consulta OpenCode, Ollama e NVIDIA antes de permitir a liberacao.
  Se o modelo estiver trabalhando, mostra a tarefa e a pasta e nao executa o stop.

Ao abrir o OpenCode pela primeira vez, informe a mesma senha usada no Maestro. O
aplicativo valida essa senha pelo controle privado, alinha automaticamente o cofre
DPAPI do OpenCode e a guarda cifrada pelo Android Keystore. Nas proximas vezes o
OpenCode abre sozinho. A senha nunca e embutida no APK ou registrada em log.

### Pela maquina, com USB debugging

Conecte o telefone e execute `INSTALAR_NO_ANDROID.bat`. O instalador usa o Android SDK ja presente nesta maquina e preserva uma instalacao beta anterior.

## Recursos desta versao

- downloads HTTP e blob conferem o tamanho completo antes de salvar o arquivo;
- respostas HTTP parciais e transferencias interrompidas nao anunciam sucesso;
- arquivos recebidos ficam em cache privado ate a verificacao, com descarte ao falhar;
- aguarde o download terminar com o aplicativo aberto; esta beta nao tem retomada
  automatica nem servico de download em segundo plano;
- login do Maestro com cookie persistente e senha nunca embutida no APK;
- barra nativa permanente para alternar entre Maestro, OpenCode local e ComfyUI;
- senha unica Maestro/OpenCode, configurada pelo proprio aplicativo no primeiro acesso;
- login automatico do OpenCode com a senha cifrada em AES-GCM pelo Android Keystore;
- acesso privado aos servicos desta maquina somente pelo hostname exato do Tailscale;
- estado ao vivo do Qwen no painel: em uso, carregado/ocioso, liberando, livre ou indeterminado;
- atribuicao da atividade ao titulo da tarefa OpenCode e ao diretorio do projeto;
- liberacao confirmada da VRAM por uma unica acao fixa, permitida apenas apos
  ociosidade continua e bloqueada quando qualquer sensor estiver incerto;
- abertura automatica do ComfyUI depois da liberacao bem-sucedida;
- Studio Criativo, projetos, takes, historico e biblioteca da interface publica atual;
- upload de imagem, video, audio e PDF pelo seletor nativo;
- captura por camera para campos de imagem;
- gravacao por microfone nos prompts, campos de evitar e motivos de reprovação;
- recuperacao guiada quando o microfone e negado: nova tentativa com explicacao e
  atalho para a permissao do aplicativo quando o Android bloqueia novas perguntas;
- envio de arquivo de audio como alternativa ao microfone, com transcricao local
  pelo Faster Whisper em CPU/int8 e descarte do audio depois do uso;
- reproducao de imagem, audio e video dentro do Studio;
- downloads HTTPS autenticados salvos no local escolhido pelo usuario;
- download direto dos takes prontos, aprovados, em upscale ou finais;
- reprovação com motivo obrigatorio e envio rastreavel ao diretor;
- suporte aos downloads `blob:` produzidos atualmente pelo JavaScript do Maestro;
- navegacao de voltar, barra de carregamento, tela de reconexao e sessao preservada;
- acesso aos subdominios Pemara autorizados pelo gateway;
- interface fluida para celular, notebook e desktop, sem zoom-out de pagina desktop;
- acoes principais, solicitacao de fotos-base e upscaling acessiveis em telas compactas;
- primeira navegacao identificada pela versao `1.0.0-beta.11` e assets web versionados, evitando layout antigo em cache;
- atualizacao do APK invalida somente o cache web antigo e preserva cookies/login;
- retorno ao aplicativo apos cinco minutos em segundo plano recarrega a interface publica atual;
- rolagem unica para listas de takes;
- nenhuma permissao permanente de camera nem acesso amplo ao armazenamento; a
  permissao de microfone e solicitada somente quando o usuario toca em **Falar**.
- launcher oficial com o mascote Pemara, suporte a mascaras adaptativas, icone
  circular e variante monocromatica para o tema do Android.

## Identidade visual

- Icone mestre: `branding/Pemara-Maestro-App-Icon-1024.png`;
- visualizacao das mascaras: `branding/Pemara-Maestro-App-Icon-preview.png`;
- os recursos Android derivados ficam em `app/src/main/res`.

## Desenvolvimento

Requisitos usados nesta maquina:

- JDK 21 do Android Studio;
- Android SDK 36;
- Android Gradle Plugin 8.11.1;
- Gradle 8.14.

Comandos de validacao:

```powershell
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
$env:ANDROID_HOME="$env:LOCALAPPDATA\Android\Sdk"
.\gradlew.bat testBetaUnitTest lintBeta assembleBeta
```

O APK gerado fica em `app/build/outputs/apk/beta/app-beta.apk`.

## Limite conhecido da entrega

Nao havia telefone conectado nem imagem de emulador instalada durante a compilacao. O pacote passou por compilacao, R8, testes unitarios, lint bloqueante, verificacao do manifesto, verificacao criptografica da assinatura e testes HTTP dos servicos e controles privados. O teste final da senha unica, toque, teclado, camera, microfone e seletor de arquivos deve ser feito no aparelho que receber o APK.
