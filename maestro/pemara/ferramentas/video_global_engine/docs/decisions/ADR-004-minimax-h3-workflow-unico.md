# ADR-004 - MiniMax H3 como unico motor de video do Maestro

- Estado: aceito
- Data: 2026-08-16

## Contexto

Wan foi removido e LTX foi recusado para producao por alucinacoes. A coexistencia de defaults,
templates e documentacao de motores antigos criava ambiguidade. A producao recente tambem provou
que ancora ruim contamina identidade, anatomia e estilo, e que transicao editorial por crossfade ou
quadro congelado viola a continuidade.

## Decisao

O MiniMax H3 e o unico motor autorizado a gerar video. O workflow canonico e:

`roteiro -> ancoras aprovadas -> prompt H3 oficial -> preflight -> take H3 -> QC humano -> conectores H3 -> picture lock -> FHD60 -> Foley -> master`.

Agentes e skills sao roteados por etapa. Nenhum agente aprova candidato. Qwen/FLUX permanecem
permitidos para imagem; RIFE, RealESRGAN, NVENC e HunyuanVideo-Foley permanecem pos-processamento.

## Consequencias

- O painel e a API expõem uma fonte de verdade unica.
- Templates novos deixam de criar perfis LTX/Wan.
- Projetos historicos continuam legiveis, mas motor antigo nao ganha fallback silencioso.
- Crossfade, freeze, hold, reset e cauda estatica falham fechado.
- Ganhos de velocidade com risco de qualidade ficam em laboratorio.
- Aprovacao humana permanece obrigatoria em ancora, visual, picture lock e audio.

## Rollback

Restaurar o snapshot anterior do codigo sem apagar projetos, modelos ou candidatos. Nunca reativar
motor antigo por fallback; qualquer mudanca de motor exige novo ADR e autorizacao do proprietario.
