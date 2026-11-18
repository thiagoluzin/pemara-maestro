# Contrato de produção musical

Qwen 3.8 coordena letra original, idioma, estilo, BPM proposto, duração e arco por seções.
Letra fornecida, duração manual, motor e instrumentos explicitamente escolhidos são preservados.
YuE2 é o padrão; indisponibilidade não autoriza substituição. ACE-Step e outros motores de criação
continuam disponíveis somente por escolha explícita.

## Ordem do trabalho

1. Fixar intenção, idioma, motor, instrumentos, voz, limites de duração e referências musicais amplas.
2. Carregar composição/letra, arranjo, mix e revisão de escuta conforme o fluxo obrigatório.
3. Qwen propõe plano validado em JSON com papéis, energia e solista por seção. Sem análise musical
   fornecida, marcadores são propostas. Qwen textual não escuta áudio nem mede BPM.
4. Escolher geração direta ou partitura original no YuE2 conforme a direção. Geração direta não
   exige transcrição ou MIDI intermediário. Letra, melodias e riffs de nova composição são originais.
5. Na saída nativa YuE2 há uma mix. Ganhos, instrumentos e BPM descritos no prompt não comprovam
   controle real de stems ou realização exata no áudio. Inspecionar o resultado efetivo.
6. Checar WAV e MP3 finais: decode, taxa/canais, duração mínima e máxima pedidas, amostras não
   finitas, clipping e true peak até -1 dBTP. LUFS informa escuta; não é uma nota artística.
7. Ouvir a música integral e trechos críticos; avaliar identidade, canto, timbre, arranjo, dinâmica,
   mix e finalização separadamente. Candidato tecnicamente rejeitado não pode ser promovido.

## Direção e revisão

Registro de crítica: tempo → defeito ouvido → efeito musical → causa → correção proposta.
Comparar A/B com volume de escuta equivalente quando houver referência autorizada. Dar prioridade
ao canto e ao hook; versos com espaço, refrões com contraste e transições com causa musical.
Não mascarar instrumentos com guitarra contínua nem confundir plano textual com execução.
Preservar fontes, aprovados, rejeitados, histórico e decisão exata do proprietário.

## Sistemas retirados e dependências compartilhadas

Reinstrumentação, MuScriptor/Partitura Primeiro, produtor por stems e cover ACE-Step do Maestro
foram retirados por ordem do proprietário em 2026-10-16. Não usar instaladores históricos ou
reinstalar pesos para cumprir este contrato. Histórico e downloads anteriores permanecem.

Preservar criação original YuE2/ACE-Step, Qwen, helpers de áudio, instrumentos/sfizz usados no vídeo
Tema 2, MuseScore, separação Demucs de outros projetos e MERT do ControlFoley. Dependência
compartilhada não é licença para reativar a função retirada.

Instalar skills não autoriza geração, publicação, compra, treino ou troca de motor. Codex opera
ComfyUI exclusivamente pelo MCP; backend Maestro permanece autônomo. TypeSafe mantém o Qwen
escolhido e a validação determinística; nenhuma chamada paga por mera presença desta skill.

Implementação ativa: `music_qwen.py`, `music_writer.py`, `music_creation.py`, `music_delivery.py`
e `music_ai_audio.py` em E:/Pemara/maestro/pemara/services/studio/.
Manifesto: E:/Pemara/cleanup_manifests/reinstrumentation_removal_20261016/.
