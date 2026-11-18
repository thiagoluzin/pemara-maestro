# YuE2: duração e encerramento

Atualização de 2026-10-05: teto do Maestro liberado para **900 segundos (15 minutos)**, por instrução do proprietário. O padrão inicial permanece 30 segundos; a duração é escolhida no formulário. O catálogo vivo do ComfyUI 0.37.0 confirmou o máximo nativo de 900. Essa é uma capacidade do parâmetro, não um benchmark de quinze minutos nem garantia de qualidade em qualquer letra/contexto.

## Causa verificada

O job `680685c4495e41beb96aa062317b77b2`, “Rei das Antenas”, recebeu 180 segundos. Seu ABC prevê aproximadamente 271,58 segundos em 190 BPM e seu FLAC tem exatamente 180 segundos. Portanto, o encerramento previsto ficava além do orçamento. O arquivo e a letra originais foram preservados.

## Fluxo automático implantado

- O escritor local recebe duração e reserva para o encerramento, com uma letra completa e concisa.
- Planejamento e áudio seguem automaticamente dentro de um único job do Maestro, também em músicas longas e instrumentais.
- O código mede a duração do ABC somando cada voz separadamente e usando a maior duração, respeitando andamento, unidade, compassos, pausas e frações.
- Quando necessário, compacta somente frases completas e alinhadas, preservando andamento, primeira frase vocal por seção e última frase original. Prioriza a remoção de introduções, interlúdios e passagens esparsas. A partitura original fica registrada.
- Notação não suportada ou composição que não cabe provoca recomposição limitada a três tentativas. Não presume uma duração válida.
- O grafo mostra `yue2_truncated` e os segundos reais com PreviewAny. Um áudio que esgotou o orçamento antes do token de fim provoca uma nova tentativa com composição menor; após duas falhas o job informa o problema, sem declarar a música concluída.
- Não aplica corte, fade ou aceleração para disfarçar uma composição incompleta. O áudio continua pendente da avaliação artística do proprietário.
- O modo manual com revisão de ABC e os demais motores permanecem disponíveis.

## Validação

Suite original e contratos de encerramento: 43 testes passaram; teste adicional do teto de 900 passou na suite de dez testes do módulo de encerramento. Compilação Python passou. Validação dos grafos pelo MCP não apresentou erros.

Uma versão separada da música usa o mesmo estilo, a letra original e a partitura original compactada para 170,53 segundos. O render real, pelo MCP, terminou em **169,96 segundos**, `yue2_truncated=False`, dentro do pedido de 180. O RMS dos últimos 100 ms caiu de -20 dB no original para -76 dB na nova tentativa. Esses sinais comprovam fim técnico e decaimento, não aprovação artística.

Candidate: `music-ending-rei-das-antenas-20261005-attempt01`, “Rei das Antenas — encerramento (teste)”, disponível no Maestro com MP3. Prompt Comfy: `b75abdf0-1f2b-4fbb-a3cd-a4ba9aa0f7aa`. Evidências em `outputs/music_ending_20261005/`. Backup pré-alteração: `backups/music_ending_20261005_154344/`.

## Opção de duração escolhida pelo modelo

Adicionada em 2026-10-05 por solicitação do proprietário: checkbox **Deixar o modelo decidir a duração**, visível ao selecionar YuE2. Inicialmente desmarcada. Marcada, desativa o campo de tempo manual e envia `music_duration_auto=true`; desmarcada, restaura o campo sem substituir o valor digitado.

No modo escolhido pelo modelo, o escritor recebe duração `null` e a instrução de escolher uma estrutura completa adequada à ideia. O compositor recebe liberdade de duração; **900 segundos é um teto de segurança, não um objetivo que precisa preencher**. O áudio termina no token de fim do YuE2, com as verificações de encerramento já implantadas. Não exige que o usuário informe tempo nem letra. A escolha é persistida no job e preservada nas repetições.

A opção não muda ACE-Step, LeVo, SFX nem vídeo. Requests incompatíveis ou valores não booleanos são rejeitados no backend. Formulários antigos mantêm o tempo manual.

Validação após a mudança: **50 testes passaram**, incluindo passagem da opção pelo formulário, persistência, repetição, liberdade nas instruções do escritor e compositor, teto 900 e manutenção da duração manual. Python compilou e JavaScript passou em `node --check`. Nenhuma nova música foi solicitada para testar esta alteração de interface.

Build: `20261005-music-duration-choice-v1`. Backup pré-alteração: `backups/music_duration_choice_20261005_162137/`.

Publicado pelo supervisor do Studio. Verificado na página pública: checkbox marcado desativa o tempo manual; desmarcado reativa o campo e preserva os 180 segundos digitados durante o teste. Screenshot: `outputs/music_ending_20261005/maestro_duracao_modelo.png`. O teste de interface não enviou um job de geração.

## Referências

- https://github.com/Comfy-Org/docs/blob/main/tutorials/audio/yue2/yue2.mdx — teto, contexto, orçamento e token de fim.
- Catálogo vivo MCP `YuE2GenerateMusic`, consultado em 2026-10-05.
- Skill TypeSafe obrigatória e documentação viva de construção: manter regras e cálculos em código. Este ajuste não usa API paga nem envia música/letra a um serviço externo.
