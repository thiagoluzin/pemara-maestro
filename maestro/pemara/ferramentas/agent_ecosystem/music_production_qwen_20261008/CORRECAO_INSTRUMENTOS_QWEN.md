# Correção do contrato Qwen após os erros na criação vocal

Em 08/10/2026 o proprietário mostrou a mensagem “Plano Qwen com instrumentos invalidos” em um pedido de heavy metal britânico, letra em inglês e cinco minutos. Os logs confirmaram quatro falhas dessa categoria. As respostas brutas dessas tentativas antigas não eram persistidas, portanto não é possível afirmar quais chaves específicas o modelo escreveu em cada uma.

## Falhas corrigidas

O contrato de decodificação permitia nomes livres de pistas, enquanto a validação aceitava um conjunto restrito. Além disso, `vocals` era autorizado como solista de seção, mas não como pista de criação. O contrato agora fornece ao Qwen o mesmo vocabulário fechado usado pela validação, incluindo `vocals` na criação. Na reinstrumentação o conjunto permanece exatamente o escolhido; não se adiciona uma nova voz nem se altera a voz preservada.

O primeiro teste real da correção também revelou energia de seção fora da faixa permitida. O prompt de criação não explicava sua escala. Agora o schema e o prompt explicitam energia entre 0 e 1, além dos limites de BPM, ganho, densidade, velocidade, duração e tamanho dos campos. Erros numéricos informam a faixa e o valor recebido para que o modelo consiga corrigir o campo.

Uma resposta inválida de planejamento recebe uma única tentativa de correção pelo mesmo Qwen local, com erro detalhado, contrato e pedido original. A validação continua obrigatória. Falha de serviço/VRAM não dispara essa correção de conteúdo; cancelamento permanece respeitado. Escolhas explícitas de letra, instrumental, duração e BPM continuam protegidas.

O teste real seguinte permitiu registrar o erro restante: ambas as respostas tinham seções com guitarra/baixo, mas somente pistas de bateria, percussão e voz. A correção passa a exigir, no schema da segunda resposta, todas as pistas válidas já declaradas pelo modelo em pistas, instrumentos de seção e solistas. O Qwen continua definindo seus parâmetros; código não fabrica ganhos, papéis ou novas performances. As respostas reprovadas desse teste foram preservadas no backup `live_responses_before_required_repair.json`.

## Verificação

`test_music_writer_contract.py` cobre o pedido vocal de cinco minutos, pista vocal, schema fechado, pista desconhecida/vazia, correção limitada, energia em percentual, JSON incompleto, escolhas explícitas, cancelamento e falhas do serviço. O log `tests_instruments_fix.log` registra o resultado final da suíte musical.

Resultado final: **127 testes musicais passaram**; módulos Python compilaram. Studio reiniciado pelo supervisor oficial em momentos sem jobs/lease próprios ativos, com resposta autenticada HTTP 200 depois da atualização.

A última revisão do escritor foi salva às 11:47:57. O novo pedido do proprietário `186bcc842466435885e0eec1930dac8e`, iniciado às 11:48:13, passou pelo planejamento/validação do Qwen e chegou à geração ComfyUI, prompt `e32af197-3d8a-4933-bbf9-73a27eac0e3d`, sem erro nessa etapa. A fila real foi conferida pelo MCP. Esse pedido utiliza o escritor importado depois da revisão; não foi cancelado, reenviado ou reiniciado. A geração de áudio ainda estava em andamento no registro, portanto isso não comprova entrega, duração final, inteligibilidade ou qualidade artística.

`verify_qwen_instruments_fix.py` testa apenas o planejamento textual com o pedido da imagem, usando duração escolhida pelo modelo, como estava no pedido real do Maestro. O script não envia áudio. A resposta real válida, quando concluída, fica em `qwen_instruments_fix_live_plan.json`; respostas do teste ficam em `qwen_instruments_fix_live_responses.json`. Esses arquivos são evidência local, não aprovação de uma música.

As verificações textuais isoladas anteriores expuseram as falhas intermediárias descritas acima e não são registradas como aprovadas. A evidência real de superação do erro após a correção final é o novo pedido autônomo do proprietário, já admitido na etapa ComfyUI. A ocupação da GPU por essa música impede repetir o teste isolado em paralelo com segurança.

Atualização final: o pedido do proprietário concluiu (`done`, sem erro) e o MCP confirmou o áudio `ba557dd6-034d-4dc2-be5a-65a96daa2604` como `completed`. `qwen_instruments_fix_owner_success.json` registra o plano real: inglês, música vocal, guitarra/baixo/bateria/voz, BPM 128 e 300 segundos propostos. A saída efetiva YuE2 tem **243,96 segundos (4min04s)**, encerramento dentro do limite escolhido e QC técnico aprovado no MP3: decode completo, sem clipping ou amostras não finitas, true peak -5,9 dBTP. O resultado não deve ser apresentado como duração exata de cinco minutos. A música e sua qualidade continuam pendentes da escuta/aprovação do proprietário. Essa execução real completa dispensa repetir o teste textual isolado para comprovar a correção.

Backups anteriores à correção: `E:\Pemara\maestro\pemara\backups\music_qwen_instruments_fix_20261008`. A ativação reinicia somente o Studio pelo supervisor oficial, após os trabalhos ativos e a lease terminarem. Não se cancelam músicas/takes nem se reinicia o ComfyUI para aplicar a correção. O recibo final de testes e ativação fica em `qwen_instruments_fix_receipt.json`.
