# Contrato de produção musical

Qwen 3.8 é o coordenador musical local escolhido pelo proprietário. Na criação automática,
define letra original, idioma, estilo, BPM proposto, duração e arco por seções. Letra fornecida,
duração manual, motor e instrumental explicitamente escolhido são imutáveis. Na reinstrumentação,
planeja a produção; não reescreve letra, cantor, notas protegidas, andamento da fonte ou duração.

## Ordem do trabalho

1. Identificar criação original ou adaptação. Fixar intenção, motor, fonte, instrumentos, voz e limites.
2. Fonte de cover: preservar bytes/hash e inspecionar duração/codec; preferir stems e partitura corrigida.
3. Qwen propõe plano validado em JSON com papéis, ganhos, energia e solista por seção. Sem análise
   musical fornecida, marcadores são propostas. Qwen textual não escuta áudio nem mede BPM.
4. MuScriptor é rascunho; comparar MIDI/prova A/B com a gravação. Revisão do proprietário fixa hash.
5. Voz: stem fornecido alinhado ou Demucs local. Ouvir segunda voz, sílabas, reverb, sibilantes,
   vazamento instrumental e sincronismo. Igualdade de duração não comprova alinhamento musical.
   Hash bloqueia o asset vocal revisado; separação não recupera necessariamente o stem verdadeiro.
6. Renderizar pistas independentes. Contrato MIDI protege notas/ataques/durações. Novas camadas de
   acompanhamento devem ter contrato próprio; não usar base generativa para substituir a referência.
7. Qwen controla ganhos e pequenos contrastes suaves por seção. Notas protegidas não são apagadas
   para produzir pausas. Voz preservada não recebe essa automação; master tem processamento próprio.
8. Checar WAV e MP3 finais: decode, taxa/canais, duração, amostras não finitas, clipping e true peak
   até -1 dBTP. LUFS informa escuta; não é uma nota artística nem meta universal de volume.
9. Ouvir música integral e trechos críticos; avaliar separadamente identidade, canto, timbre,
   arranjo, dinâmica, mix e finalização. Candidato tecnicamente rejeitado não pode ser promovido.

## Direção e revisão

Registro de crítica: tempo → defeito ouvido → efeito musical → pista/causa → correção proposta.
Comparar A/B com volume de escuta equivalente, voz solo, base solo e mix completa. Dar prioridade
ao canto e ao hook; versos com espaço, refrões com contraste e transições com causa musical.
Não mascarar instrumentos com guitarra contínua, confundir MIDI duplicado com duas performances,
ou chamar soundfont de guitarra gravada. DI FreePats é um instrumento amostrado com saturação/EQ;
a cadeia leve não equivale a amplificador capturado nem garante articulação real de palm mute.

## Limites e qualificação

ACE-Step cover é experimental: pode variar melodia/voz. MuQ/MERT ajudam a comparar e diagnosticar,
mas similaridade não prova cópia fiel. BS-RoFormer/Mel-Band e modos ACE lego/complete são extensões
a qualificar por checkpoint/configuração/licença e referência; não escolher automaticamente.
Não prometer 100% de fidelidade a um mix. Hash de asset e igualdade MIDI são provas limitadas.
Original, tentativas rejeitadas e histórico são preservados. Instalar skills não autoriza render,
publicação, compra, serviço pago, troca de motor ou treino. Codex opera ComfyUI exclusivamente
pelo MCP; backend Maestro permanece autônomo. TypeSafe obrigatório mantém o Qwen escolhido
e validação determinística; nenhuma chamada paga por mera presença desta skill.

Implementação: E:/Pemara/maestro/pemara/services/studio/music_qwen.py, music_writer.py,
music_score_first.py, music_vocals.py, music_delivery.py e music_ai_audio.py.
