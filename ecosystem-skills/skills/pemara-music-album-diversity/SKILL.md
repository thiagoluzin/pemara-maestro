---
name: pemara-music-album-diversity
description: "Planeja e revisa diversidade entre músicas de um lote ou álbum, detectando reciclagem de hooks, riffs, grooves, formas e fraseado sem apagar a identidade da banda."
---

# Identidade e diversidade do álbum

Use para lotes e ao receber crítica de músicas repetitivas. Atue junto do gênero escolhido e do produtor. Leia a [evidência](../pemara-music-production-lead/references/quality-evidence.md). Não reaproveite músicas rejeitadas ou apagadas como base; preserve apenas as decisões abstratas ainda válidas.

## Mapa antes do lote

Descreva por faixa: ideia/narrador, hook, motivo principal, groove e acentos, curva de energia/forma, fraseado vocal e papel no álbum. Compare vizinhas e também as mais semelhantes do conjunto. Não montar vinte faixas a partir de um template único com BPM e seed diferentes.

Mantenha o que dá identidade à banda, como cantor, paleta de timbres e linguagem musical. A diferença precisa existir em escolhas centrais: um hook novo com outro motivo/groove e desenvolvimento, por exemplo. Mudar simultaneamente cantor, produção e gênero em cada faixa não é a solução obrigatória.

Formas simples podem se repetir no punk e riffs podem retornar dentro da mesma música. O problema é a reciclagem predominante de composição e interpretação entre canções sem intenção. Título, sinônimos, seed ou transposição isolados não demonstram diversidade.

## Comparação e ferramenta

`scripts/audit_album.py` recebe JSON com `tracks`: cada item tem `id`, `title`, `lyrics`, `hook` e `arrangement`, que pode conter `riff_signature`, `rhythm_signature`, `form` e `vocal_phrasing`. As assinaturas são descrições/células comparáveis fornecidas pelo arranjador, não medidas automaticamente do áudio.

Execute `python scripts/audit_album.py plano.json --out comparacao.json` no runtime existente. A ferramenta marca cópias textuais e combinações de assinaturas iguais; similaridade de palavras é apenas triagem. Ela não detecta transposição por ouvido, riffs tocados ou qualidade musical. Dados ausentes ficam explícitos; não inventar assinaturas para “passar”.

Revise as sinalizações no plano e depois compare áudios completos em volume equivalente. Registre pares, intervalos efetivamente ouvidos, semelhança percebida e decisão. Uma matriz escrita diversa pode produzir áudios repetitivos; hashes diferentes não afastam esse problema.

## Correção

Quando duas músicas soarem iguais, identifique a combinação dominante que se repetiu e redesenhe a composição/fraseado pertinente. Não começar pela troca aleatória de seed nem pela inserção de uma ponte idêntica em todo o lote. Preserve o que o proprietário já aprovou e a autorização de correção existente.

Após um piloto aprovado como direção, prossiga no escopo autorizado com revisão por faixa e comparação do conjunto; a prévia não aprova o lote inteiro. Crítica recorrente pede mudança demonstrável de método, não multiplicação das tentativas. Geração cancelada permanece cancelada.
