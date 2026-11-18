# Motores de música do Maestro — pesquisa em 05/10/2026

O Maestro tem mais motores e pesos locais do que o seletor de Criar música mostra. A prioridade recomendada é integrar ao formulário o ACE-Step e o YuE2 já presentes, com execução real, estado de disponibilidade e controles próprios. Esta pesquisa não instalou, atualizou ou executou modelos; não houve geração de mídia ou chamada paga.

## Estado conferido no ambiente

| Motor ou fluxo | Evidência atual | Acesso no Maestro | Limitação atual |
| --- | --- | --- | --- |
| LeVo 2 / SongGeneration v2-large | Studio informa `installed=true`, `configured=true`; runtime dedicado não estava online | Criar → Criar música | Integração limitada a pilotos de 5–15 s; limite do Maestro, não uma afirmação sobre a capacidade total do modelo |
| ACE-Step 1.5 XL Base | Arquivos de pesos presentes; `/api/music-reinstrument/status` informa `configured=true` | Reinstrumentar → ACE-Step experimental | Worker exige áudio de origem e executa `task_type=cover`; não há registro dele entre os provedores de criação por texto |
| ACE-Step 1.5 Turbo e LMs 1.7B/4B | Pesos presentes no runtime musical | Não expostos como escolhas no Criar música | Presença dos pesos não comprova inferência atual nem qualidade |
| YuE2 3B INT8 | Checkpoint de 3.960.938.800 bytes; quatro nós reconhecidos no runtime ativo pelo MCP | Workflows locais do ComfyUI | Não registrado no seletor musical do Maestro |
| YuE2 GGUF | Arquivos Q8 e VAE presentes no diretório audio_cpp | Fora do Criar música | Inferência desta alternativa não foi testada nesta pesquisa |
| MusicGen-Style 1.5B | Cache contém `state_dict.bin` e `compression_state_dict.bin` | Não encontrado no registro de provedores do Criar música | Cache de pesos, sem prova de serviço configurado |
| Lyria / Vertex | Provedor registrado, `configured=false` no Studio | Opção indisponível no Criar música | Adapter ainda usa `lyria-002` por padrão; disponibilidade de credenciais em outro aplicativo não equivale à configuração do Maestro |
| Stable Audio | Provedor registrado, `configured=false` | Opção indisponível | Nenhum endpoint local ou chave reconhecido pelo Studio |
| ElevenLabs Music | Provedor registrado, `configured=false` | Opção indisponível | Nenhuma chave reconhecida pelo Studio |
| Partitura Primeiro / produtor por stems | Ambos informam `configured=true` | Reinstrumentar | São fluxos de transcrição/arranjo de uma fonte, não geradores de canção original por texto |

O catálogo musical é produzido em `services/studio/main.py::_audio_provider_status`. O frontend lê esse catálogo em `app/assets/maestro.js::genAudioProvidersForMode`. Por isso simplesmente adicionar nomes ao HTML não entrega a funcionalidade.

Diretórios conferidos: `ferramentas/audio_neural`, `D:/PemaraModels/workflows_20260920`, `D:/PemaraAI/huggingface-home/hub`, `D:/PemaraModels/hf_cache` e os workflows do runtime ativo. Não foi feita busca exaustiva de todos os discos. HeartMuLa, MuLaCover e Stable Audio 3 não foram encontrados nesses caminhos como instalações utilizáveis.

## Validação atual sem geração

O MCP confirmou ComfyUI ativo em `127.0.0.1:8188`, workspace `D:/PemaraRuntimes/ComfyUI-v0.36.0-pemara`, RTX 5090 com capacidade nominal de 32 GB. A consulta automática de atualização do comfy-cli expirou; não produziu conclusão de versão atualizada.

Os workflows abaixo passaram pela validação MCP contra o catálogo vivo, com zero erros, zero avisos e sem nós pagos:

- `PEMARA_IMAGE_AUDIO/10a_YuE2_planejar_ABC_sem_audio.json`: 3 nós convertidos e verificados.
- `PEMARA_IMAGE_AUDIO/10b_YuE2_gerar_com_ABC_revisado.json`: 7 nós convertidos e verificados.

Nós presentes: `YuE2GenerateABC`, `YuE2GenerateMusic`, `EmptyYuE2LatentAudio`, `SheetSage2AudioToABC`. Validação estrutural não comprova áudio, memória suficiente durante execução, fidelidade da partitura ou qualidade artística.

## Atualizações e melhorias pesquisadas

### ACE-Step

O checkout instalado está em `14c0211d5a0653b0f63e27686f4c3f151b4d8629`, de 16/08/2026. O HEAD oficial consultado foi `ca1e85fe9430179831e6bc6be790c332190a3866`, de 29/08/2026: 11 commits à frente. Entre as correções estão memória KV, seed, parâmetros de cover e carregamento explícito de modelo. Recomenda-se atualizar em ambiente isolado e revalidar o worker. XL SFT/Turbo são opções oficiais a comparar; somente XL Base e Turbo 2B foram encontrados localmente. O projeto oferece criação por texto, edição de trechos e controles de BPM, tom e letra. [Repositório oficial](https://github.com/ace-step/ACE-Step-1.5), [API de inferência](https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/INFERENCE.md).

### YuE2

O repositório oficial publicou instrumental/covers em 25/09, relatório do modelo em 26/09 e relatório SheetSage2 em 02/10. A API permite salvar o plano antes de sintetizar e preservá-lo entre versões. A documentação separa o VAE para escuta do decoder usado nos benchmarks. Recomenda-se integrar planejamento, revisão ABC e geração ao Maestro, preservando referências e versões. O HEAD consultado foi `f75145ddbd6b3287ea88f637139e21ceb2d7c811`, de 05/10. Isso não comprova que o checkpoint INT8 local corresponda aos novos pesos oficiais. [Fonte oficial](https://github.com/multimodal-art-projection/YuE), [Guia de geração](https://github.com/multimodal-art-projection/YuE/blob/main/docs/generation.md).

### YuE2-Turbo

É uma camada de execução acelerada, usando o mesmo modelo BF16 e 32 passos. O autor reporta 1,68× por canção e 3,31× de vazão com quatro pedidos em RTX 5090. O ambiente testado é Linux, PyTorch 2.10/CUDA 12.8 e vLLM 0.19; mantém aproximadamente 18 GB residentes. Esses números não foram reproduzidos neste Windows. Recomendação: laboratório separado, com liberação da GPU ao terminar e comparação com o caminho ComfyUI existente. [Fonte do implementador, reconhecida pelo projeto YuE2](https://github.com/NoizAI/YuE2-Turbo).

### LeVo 2

A versão oficial consultada permanece LeVo 2. A documentação descreve letra por seções, tags musicais, geração instrumental e saídas separadas de voz/acompanhamento. São melhorias possíveis para o formulário atual. A licença consultada restringe o software e pesos a uso acadêmico, pesquisa e educação; manter esse escopo. Os snapshots locais SongGeneration e LeVo2_runtime são de junho e fevereiro, respectivamente; não foi demonstrada correspondência exata ao repositório atual. O antigo endereço Tencent retornou 404, portanto não deve sustentar uma atualização automática. [Documentação atual](https://github.com/levo-demo/LeVo), [Licença](https://github.com/levo-demo/LeVo/blob/main/LICENSE).

### Stable Audio 3

Lançamento oficial em 20/05/2026. Small Music gera até dois minutos; Medium até 6:20. Há edição e extensão de trechos, e pesos disponíveis para Small SFX, Small Music e Medium. É candidato para trilhas instrumentais e efeitos; não foi instalado ou comparado aqui. O download Medium exige aceite de condições e compartilhamento de contato no Hugging Face. [Anúncio oficial](https://stability.ai/news-updates/meet-stable-audio-3-the-model-family-built-for-artistic-experimentation-with-open-weight-models), [Modelo Medium](https://huggingface.co/stabilityai/stable-audio-3-medium).

### HeartMuLa e MuLaCover

HeartMuLa oferece geração por letra/tags; a versão 3B publicada usa HeartCodec e carregamento sob demanda. MuLaCover foi publicado em 16/09 e controla covers por áudio ou MIDI de melodia/acordes. É uma alternativa para comparação de reinstrumentação. Seu ambiente validado é Linux/B300; os pesos e resultados de MuLaCover têm restrição não comercial. Isso é distinto da licença Apache do código e da licença do HeartMuLa 3B. Ambos exigem implantação e avaliação local antes de aparecer como disponíveis. [HeartMuLa](https://github.com/HeartMuLa/heartlib), [MuLaCover](https://github.com/HeartMuLa/MuLaCover).

### Alternativas de menor prioridade e nuvem

- MusicGen-Style tem pesos locais e condicionamento por estilo, mas não serviço configurado no Maestro. Manter como candidato secundário. [Modelo oficial](https://huggingface.co/facebook/musicgen-style).
- DiffRhythm tem caminhos para canções longas e edição; o repositório consultado lista pesos 1.2 e referências de pesquisa DiffRhythm 2. Não foi demonstrada uma instalação atual de DiffRhythm 2 aqui. [Fonte oficial](https://github.com/ASLP-lab/DiffRhythm).
- Google documenta atualmente Lyria 3.5, com voz/letra e estrutura de canção. O adapter legado Vertex do Maestro precisa de integração específica com a API atual; mudar apenas o nome do modelo não basta. Não foi feita chamada ao serviço. [Documentação oficial](https://ai.google.dev/gemini-api/docs/music-generation).
- Eleven Music documenta v2/v2.5, referência de áudio e edição de seções. Sua integração atual precisa ser conferida contra esses contratos se o proprietário escolher a opção paga. [Documentação oficial](https://elevenlabs.io/docs/overview/capabilities/music).

## Ordem recomendada de implementação

1. Integrar ACE-Step e YuE2 ao Criar música, com adapters reais, status honesto, seleção explícita e sem fallback. Expor letra separada do estilo, instrumental, duração, seed e controles suportados por cada motor.
2. Atualizar o ACE-Step em ambiente isolado, preservando o checkout/worker atual e recibos fixados; testar compatibilidade antes de ativar.
3. Acrescentar ao YuE2 revisão de plano ABC, arquivo de partitura e comparação de versões, mantendo o áudio original e o estado de revisão humana.
4. Comparar candidatos com os mesmos briefs: canção PT-BR, instrumental cinematográfico e arranjo de fonte autorizada. Julgar pronúncia, estrutura, materiais sonoros e continuidade, além de duração/decode/clipping. Nenhum ranking aprova mídia.
5. Avaliar Stable Audio 3 e HeartMuLa em laboratório separado; deixar MuLaCover e YuE2-Turbo dependentes de compatibilidade comprovada com o ambiente escolhido.

O gerador ACE-Step tem licença MIT, mas o fluxo atual de reinstrumentação inclui o crítico MuQ com restrição não comercial. A licença do motor não remove as limitações de outros componentes. Os termos do YuE2 distinguem criadores individuais e empresas; consultar os termos aplicáveis antes de escolher um motor para campanhas da Pemara. [Termos YuE2](https://github.com/multimodal-art-projection/YuE/blob/main/MODEL_LICENSE).

Skill obrigatória `typesafe-ai` consultada, incluindo o índice vivo. Cadastro de motores, limites conhecidos e disponibilidade devem permanecer em código; esta pesquisa não precisou enviar dados ao TypeSafe nem adicionar API. [Índice vivo](https://docs.typesafe.ai/llms.txt).
