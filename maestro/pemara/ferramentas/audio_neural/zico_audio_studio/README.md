# ZICO Audio Studio 1.0

Pacote Windows para transformar geração de voz, efeitos, música, reorquestração e pós-produção em serviços comandáveis por agente. Otimizado para NVIDIA RTX 5090; não depende do ComfyUI.

## Instalação

1. Extraia o ZIP em uma pasta comum (não execute dentro do ZIP).
2. Execute `INSTALAR_ZICO.bat`.
3. Escolha **Essencial** para começar ou **Estúdio completo** para todos os motores.
4. Reinicie o Windows se o instalador tiver instalado Git ou FFmpeg.
5. Abra o atalho **ZICO Audio Studio**.

O navegador abrirá a API em `http://127.0.0.1:8790/docs`. O sistema só escuta no computador local. Os pesos dos modelos são baixados pelos projetos oficiais no primeiro uso e podem ocupar dezenas de GB.

## Arquitetura

- Chatterbox Multilingual V3 / pacote PT-BR: narração e clonagem consistente.
- Qwen3-TTS: direção vocal e criação de voz.
- Fish Speech: atuação e diálogos.
- MMAudio: foley sincronizado ao vídeo.
- ACE-Step 1.5: música, cover, extração e reconstrução instrumental.
- FFmpeg: mixagem, normalização, master e anexação ao vídeo.

Cada motor fica em ambiente Python separado para evitar conflitos. O roteador escolhe a engine conforme a intenção; `POST /v1/route` pode ser chamado pelo seu agente. O núcleo fornece saúde, capacidades e mix/master funcional. Adaptadores de inferência são instalados por engine e deliberadamente isolados, pois suas APIs mudam de forma independente.

## Reorquestração

Há três políticas: `cover` permite reinterpretar; `hybrid` preserva estrutura e usa IA na execução; `strict` preserva notas/timing por MIDI e troca somente instrumentação. O preset `presets/reorchestration_strict.yaml` impede que “trocar instrumentos” vire uma composição diferente. Use apenas material próprio, licenciado ou permitido.

## Voz e consentimento

Cada voz recorrente deve ter referência limpa e registro de autorização em `voices/<id>/`. O sistema exige consentimento para clonagem. Não use a voz de terceiros sem autorização.

## Diagnóstico e remoção

- `DIAGNOSTICO.bat`: GPU, driver, FFmpeg, Python e engines.
- `DESINSTALAR_ZICO.bat`: remove o programa e seus ambientes após confirmação explícita.

## Integração do agente

```http
POST http://127.0.0.1:8790/v1/route
Content-Type: application/json

{"task":"narrar em português brasileiro com voz cinematográfica"}
```

Antes de produção comercial, confira a licença do checkpoint específico escolhido; licença do código e licença dos pesos podem ser diferentes.
