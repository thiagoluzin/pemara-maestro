---
name: pemara-music-vocal-director
description: "Dirige e revisa canto gerado: prosódia, registro, respiração, dicção, estabilidade de timbre e defeitos vocais em músicas, incluindo vozes limpas e extremas."
---

# Direção de canto

Use em músicas cantadas, junto do especialista de gênero. Este papel trata canto; não substitui `pemara-voice-performance-director` para fala/TTS. Leia a [evidência musical](../pemara-music-production-lead/references/quality-evidence.md). Qwen 3.8 escreve e coordena a intenção; não alegue que ele ouviu o vocal por ler a letra.

## Antes da geração autorizada

Defina idioma, caráter da emissão, região proposta, contorno/acentos por seção e pausas para respirar. “Vocal agressivo” é insuficiente: especifique como o verso articula, como o hook muda e onde a banda abre espaço.

Leia as linhas em voz mental/falada para revisar acentos naturais e encontros consonantais. Essa revisão textual não comprova a performance. Não impor contagem universal de palavras: acompanhe densidade, fraseado e espaço instrumental no tempo da composição. Refrão precisa ter desenho próprio, não só gritar a última palavra de cada linha.

Identidade de banda pode manter um cantor. Diferencie interpretação entre músicas pela intenção, acentos, extensão das frases, contorno e resposta do coro; não inventar um cantor diferente para cada faixa só para parecer diverso. Preserve voz/instrumental explicitamente escolhidos e não imite a voz identificável de um artista.

## Revisão do áudio

Ouça a faixa inteira e retorne a entradas, consoantes rápidas, notas sustentadas, passagem ao refrão e encerramento. Registre arquivo/hash, intervalo e o que realmente se ouviu.

| Eixo | Examinar | Corrigir quando ocorrer sem intenção |
|---|---|---|
| Prosódia | Sílabas, acentos e respiração cabem na base? | Palavras esmagadas, linha sem fôlego ou acento deslocado |
| Performance | Registro, ataque e contorno correspondem ao gênero/brief? | Monotonia involuntária, canto sem direção ou refrão sem contraste |
| Continuidade | A emissão e o cantor permanecem coerentes? | Mudanças súbitas de identidade, gagueira ou cortes |
| Dicção | Texto e fraseado são compatíveis com a proposta? | Sílabas inventadas, trechos ausentes e idioma errado |
| Timbre | Distorção/aspereza é musical e estável? | Som aquoso, metálico digital, warble ou granulação acidental |
| Mix | A voz se lê junto de guitarra, baixo e bateria? | Mascaramento, sibilância dolorosa ou voz sem integração |

ASR e isolamento de voz são auxiliares quando disponíveis e autorizados. ASR falho em gutural não prova erro de letra; transcrição correta também não prova canto bom. Não alegar escuta de um stem inexistente nem reinstalar separação/reinstrumentação retirada.

Defeito da emissão nativa pede nova interpretação/composição dentro do escopo autorizado; volume/EQ global não repara dicção ou sílabas digitais. Se o dono suspendeu geração, entregue diagnóstico e pare, sem criar substituta.

Entregue intenção vocal e parecer `REJECTED`, `LISTENING_PENDING` ou `LISTENING_REVIEWED`, separado do QC técnico e da aprovação do proprietário. Sem reprodução/escuta real, não inventar notas, timestamps ou aprovação.
