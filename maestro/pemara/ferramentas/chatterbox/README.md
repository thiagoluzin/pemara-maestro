# Voz Neural Privada do Maestro

O Editor IA usa duas camadas de voz:

1. **Microsoft Maria (pt-BR)**, já disponível localmente e sem download.
2. **Chatterbox Multilingual V3**, opcional, para voz neural e clonagem zero-shot.

O Chatterbox roda em ambiente Python isolado para não alterar as dependências do
Studio. O modelo só é carregado quando o usuário pede uma narração.

## Instalação

Execute `INSTALAR_CHATTERBOX.ps1`. Por padrão o motor, os temporários e todos os
caches neurais ficam isolados em
`E:\Pemara\maestro\pemara\ferramentas\chatterbox`. O caminho pode ser alterado
com `-InstallRoot`, mas a instalação oficial do Pemara permanece em `E:`.

O instalador:

- exige Python 3.11;
- exige pelo menos 15 GB livres antes de começar;
- cria um `.venv` isolado na pasta de instalação;
- instala a revisão oficial `5de7a54aa4e5e2baadb0182dde554908b48b85c2`
  do Chatterbox, fixada porque o pacote PyPI 0.1.7 ainda não expõe a seleção V3;
- não deixa cache duplicado do `pip`;
- reutiliza a pilha CUDA já validada do Maestro para a RTX 5090, sem manter uma
  segunda cópia CPU do Torch dentro do ambiente;
- não baixa os pesos nem inicia a GPU durante a instalação.

Os pesos oficiais do Multilingual V3 podem ser pré-carregados sem iniciar CUDA
por `preload_model.py`; caso contrário, serão obtidos na primeira geração. O
Editor exibe a voz do Windows enquanto o motor neural não estiver pronto.

Exemplo:

```powershell
powershell -ExecutionPolicy Bypass -File `
  E:\Pemara\maestro\pemara\ferramentas\chatterbox\INSTALAR_CHATTERBOX.ps1
```

Projeto oficial: https://github.com/resemble-ai/chatterbox

## Privacidade e consentimento

As amostras ficam em `dados/studio/editor_suite/voices`, na própria máquina.
Criar um perfil exige confirmação explícita de autorização de uso da voz.
O Maestro não envia a amostra ao Ollama, à NVIDIA nem a um provedor externo.
