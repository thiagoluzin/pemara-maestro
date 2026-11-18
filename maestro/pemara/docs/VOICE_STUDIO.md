# Estúdio de voz local do Maestro

## Objetivo e plano

Pedido do proprietário em 05/11/2026: uma experiência de narração e clonagem de voz semelhante ao fluxo cotidiano do ElevenLabs, dentro do Maestro, usando o Drama 3 instalado e o ComfyUI local.

1. Preservar o Drama 3 Windows instalado, seus modelos e a ponte histórica da campanha. Criar uma ponte geral independente.
2. Integrar a seção **Vozes** ao Maestro: texto, voz, interpretação, geração, escuta e download.
3. Persistir referências com transcrição e autorização; selecionar uma referência para clonar sua identidade em novos textos. Não treinar modelos nem substituir o motor.
4. Oferecer passagem única e narração longa em trechos com continuidade do próprio runtime. Preservar texto integral, sementes, parâmetros, referências, fontes, recibos e versões.
5. Validar biblioteca, fila, recuperação, cancelamento próprio, integridade, autenticação e interface responsiva. Uma execução técnica não comprova semelhança vocal, sotaque nem aprovação artística.

## Arquitetura

`Maestro → /api/studio/api/voice-studio → Studio autenticado → ComfyUI → PemaraDrama3Studio → runtime Drama 3 Windows existente`

O backend do Maestro opera autonomamente. O Codex valida e opera o ComfyUI exclusivamente por `comfyui-local` MCP. A ponte específica `PemaraDrama3Local` continua intacta.

Estado: `dados/studio/voice_studio/library.sqlite3`; arquivos imutáveis de entrada e candidatas em `voices/` e `jobs/`. Cada tentativa tem `request.json`, `workflow.api.json`, referência copiada quando escolhida, progresso, log e recibo com SHA-256. WAV é o original; MP3 é uma exportação opcional a 192 kbps. Nenhuma restauração de imagem/vídeo se aplica a áudio.

O nó a instalar em `D:/PemaraRuntimes/ComfyUI-v0.40.0-pemara/custom_nodes/pemara_voice_studio` está versionado em `services/studio/comfy_voice_studio_node/__init__.py`. A leitura de capacidade exige esse nó no runtime vivo, não apenas no disco. Reinício do ComfyUI somente com fila viva comprovadamente livre.

## Controles reais

- Texto: até 20.000 caracteres; nome da narração; voz livre ou referência persistida.
- Referência: áudio de 1–60 segundos e até 32 MB, transcrição exata, nome, descrição e autorização. Preserva o upload original e prepara cópia mono PCM de 44,1 kHz.
- Passagem única: 128–8192 quadros de áudio. Trechos com continuidade: até 65.536 quadros totais, passagens de 32–2000 caracteres, com os limites adicionais do runtime (até 32 passagens).
- Temperatura, top-p, top-k e semente são parâmetros de amostragem, não equivalentes a estabilidade/similaridade do ElevenLabs. Instruções expressivas são texto explícito editável.
- Rascunho no navegador; receita JSON por tentativa; repetir carrega os parâmetros para uma nova versão e não inicia geração.
- Uma narração ativa por vez. Reenvio com o mesmo requestId é idempotente. Erro de envio ambíguo não repete automaticamente. Reinício acompanha prompt conhecido sem reenviar.
- Cancelamento remove só o prompt próprio ainda na fila e sinaliza só seu worker. Não usa `/interrupt` global nem encerra outros programas.
- Aprovação/reprovação é humana e vinculada ao hash exato do WAV; ambas preservam o áudio.

## Limites declarados

A aba Narração usa Drama 3. A extensão de 06/11/2026 acrescenta troca de voz a partir de vídeo ou áudio com Seed-VC local e preservação da linha do tempo; consulte VOICE_CONVERSION.md. Treinamento profissional e biblioteca comercial do ElevenLabs continuam fora do escopo. EOS e integridade não comprovam leitura exata, sotaque ou fidelidade vocal; escute a candidata. O orçamento do runtime bloqueia textos com alto risco de truncamento.

TypeSafe: skill obrigatória lida e índice vivo consultado. O fluxo atual usa decisões determinísticas e permanece local, sem chamada TypeSafe nem envio de textos ou vozes a um serviço externo.

## Validação e implantação em 05/11/2026

- 15 testes novos: biblioteca, autorização, transcrição, cópia imutável da referência, autenticação, idempotência, fila ocupada, envio ambíguo, cancelamento próprio, recuperação, integridade, recibo do worker e fluxo completo em Chromium com áudio sintético de teste.
- Interface inspecionada em 320, 768, 1024 e 1440 pixels, sem transbordamento horizontal. Fluxo de cadastro, seleção, geração simulada, reprodução, download, revisão, histórico e navegação por teclado verificado. Testes usam ambiente isolado; suas referências e candidatas não entram na biblioteca real.
- 25 testes existentes de autenticação/proxy do Maestro e 12 do Studio passaram. Seis testes de navegação passaram após sincronizar a versão do frontend e retirar a dependência de números fixos de um teste de ordem da barra lateral.
- O MCP reconheceu a ponte no catálogo vivo; o grafo de qualificação passou em `validate_workflow`, com zero erros, avisos e nós pagos. Não houve submissão de nova síntese vocal nesta implantação.
- A ativação expôs uma falha anterior de identificação do listener Windows no gerenciador de ciclo de vida do ComfyUI. A correção reconhece o socket bound de um processo registrado mesmo sem linha LISTEN; quando o Windows oculta o proprietário, delega a inspeção/parada ao broker administrativo existente, que continua verificando runtime exato e fila livre. Quinze testes do gerenciador passaram. O runtime foi iniciado pelo MCP com a ponte nova.
- O Studio foi recarregado pelo supervisor Radar. Modelos, ponte da campanha e mídias existentes foram preservados.

Primeira síntese real concluída em 05/11/2026 pela interface do Maestro: voz Rui Lucato, referência original autorizada pelo proprietário no chat, job `155b81feefb441e1833f7bedac57a0da`, prompt ComfyUI `158244c1-f33e-4b11-9520-97de6735b610`. WAV mono 44.100 Hz de 20,5729 s; MP3 192 kbps. A transcrição local CPU coincidiu com as palavras normalizadas do texto solicitado; não houve amostras em escala máxima. Reprodução e download MP3 foram executados na interface, e o download teve o mesmo SHA-256 do arquivo gerado.

O primeiro teste (`2a53495f33774917816cbbc0c24e5d4d`) revelou `WinError 5` na troca atômica do JSON de progresso enquanto o painel o lia. A falha foi preservada. A correção adiciona tentativas limitadas à publicação atômica e impede que a indisponibilidade temporária do progresso aborte a síntese. Um teste de regressão reproduz o bloqueio transitório; 15 testes de backend/worker passaram após a correção. A segunda tentativa manteve voz, texto e parâmetros.

Entrega e evidências: `E:/Pemara/deliveries/drama3_maestro_rui_20261105/teste_real_01`. Pendente: escuta e avaliação humana de timbre, sotaque, naturalidade e fidelidade vocal. Execução, ASR e integridade não comprovam qualidade vocal nem equivalência ao ElevenLabs.

Fontes consultadas em 05/11/2026: documentação instalada `E:/a terra rejeita/Ferramentas/Drama3/source/docs/public/WEB_UI.md`, `fish_drama3/web_config.py`, `web_service.py`; catálogo vivo ComfyUI pelo MCP; [fluxo de TTS do ElevenLabs](https://elevenlabs.io/docs/eleven-creative/playground/text-to-speech); [índice TypeSafe](https://docs.typesafe.ai/llms.txt). As capacidades e limites implementados seguem o runtime local inspecionado.
