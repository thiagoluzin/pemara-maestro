---
name: pemara-music-listening-qc
description: Use para avaliar canções criadas, revisar letra/voz, identidade, timbres, arranjo, mix e final musical.
---

# Revisão musical

Avalie fonte e candidato integralmente. Faça comparação em volume equivalente e registre defeitos com timestamp. Diferencie nota errada na transcrição, timbre artificial, voz vazando e erro de mix. Relate o que foi realmente ouvido e o que está sem evidência. Aprovação pertence ao proprietário; sugestão do Qwen ou métricas não a substituem.

Em criação original, revisar separadamente idioma/inteligibilidade, hook, peso/energia pedidos, contraste, timbres, dinâmica e final. Identifique o arquivo/hash exato. Aprovação de direção de uma prévia não aprova automaticamente outra duração nem todo o lote. Se não houver escuta real, marque a revisão como pendente; não invente timestamps a partir da letra ou de embeddings.

Use o gênero escolhido como critério; canto exige `pemara-music-vocal-director` e lotes, `pemara-music-album-diversity`. Compare também pares de faixas em volume equivalente. Avaliar uma música isolada não demonstra diversidade de álbum.

Para triagem técnica, rode `python scripts/screen_audio.py arquivo.wav --out triagem.json` no runtime existente com numpy/soundfile. Os argumentos `--min-seconds`/`--max-seconds` só recebem limites pedidos. A ferramenta não altera a fonte, não chama GPU e não ouve música; suspeitas de silêncio, descontinuidade e clipping exigem interpretação e escuta. `NO_FLAGS` não significa aprovação artística. Leia a [evidência](../pemara-music-production-lead/references/quality-evidence.md) antes de promover qualquer resultado.

Leia o [contrato de produção musical](../pemara-music-production-lead/references/music-production-contract.md)
antes de atuar. Respeite Decision, a stack e as escolhas explícitas do proprietário.
Esses agentes são papéis; não crie subagentes sem autorização específica.
