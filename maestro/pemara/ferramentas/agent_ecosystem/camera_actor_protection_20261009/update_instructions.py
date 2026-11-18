from pathlib import Path
import json

ROOT = Path('E:/Pemara')
REF = 'E:/Pemara/.agents/skills/pemara-video-production-lead/references/camera-evidence-and-actor-protection.md'
blocks = {
 'pemara-video-production-lead': 'Para novas sequências live action com múltiplos planos, materialize o mapa único e `sequence_camera_contract.json` antes do lote. Escolha um bloco piloto que teste uma fronteira real do maior risco; o lote seguinte depende da revisão temporal desse bloco. Mantenha evidências por hash e contador de falhas por método. O backend confere o contrato antes da fila e das montagens; sua validade estrutural não comprova qualidade artística.',
 'pemara-cinematography-director': 'Ligue cada take a uma posição de câmera do mapa compartilhado, com eixo, porta/marco, percurso dos atores e trajetória de entrada/saída. Câmera fixa dirigida é válida quando torna o beat legível; não impor órbita, aproximação ou recuo a toda cena. Preserve contratos específicos já aprovados. Compare personagens e cenário antes/depois do acabamento e use proteção explícita dos atores em novas âncoras live action.',
 'pemara-film-editor': 'Planeje cada fronteira antes da geração e revise os dois intervalos móveis, incluindo direção, velocidade, fase da ação e marcos do espaço. Exija revisão temporal do bloco piloto antes de repetir a cobertura no lote. Um conector precisa entregar uma ação narrativa ausente; mudanças inexplicadas de posição ou fundo exigem fonte corrigida. Registre revisão das fontes exatas e do filme inteiro no contrato de câmera, sem inventar escuta/reprodução.',
 'pemara-live-action-continuity': 'Use o mesmo mapa e estados por take do contrato de câmera. Confira percurso dos perseguidores, portas e corpos persistentes, além da pose da vítima. Classifique a fronteira por ação ausente, corte compatível ou fonte incompatível antes de propor emenda. Registre intervalos observados e hashes. Uma câmera sustentada pode preservar continuidade; não gerar movimento gratuito para evitar um plano fixo dirigido.',
 'pemara-live-action-kinetic-supervisor': 'O handoff pertence ao mapa compartilhado: posição, escala, direção, fase, velocidade, olhar, arma, corpos e câmera nos intervalos de ambos os lados. Compare deslocamento efetivo, não somente poses. Em planos de contato/disparo, câmera fixa dirigida pode favorecer causalidade; isso não autoriza congelamento nem reduz contratos específicos de ação. Registre o parecer de fronteira no contrato de câmera.',
 'pemara-live-action-qc': 'Exija evidência temporal por fonte e fronteira do bloco piloto, depois do filme inteiro. Inclua regressões de porta sem percurso, reposicionamento do perseguidor, corpo extra, reset de pose, reação antecipada, contato fora de quadro e atores plastificados. Revise pele/cabelo/mãos/traje separados do cenário antes/depois do NR. Igualdade de pixels sob máscara comprova preservação do interior, nunca que a máscara cobre todos os atores. O modo seletivo continua pendente de qualificação visual em mídia real.',
 'pemara-cinematic-take-director': 'Receba o mapa único e as posições de câmera antes de preparar as âncoras. Materialize estado de entrada/saída e motivo de cada junção no contrato de câmera. Piloto de maior risco inclui uma fronteira; não reproduzir a estratégia no lote sem revisão temporal. Depois de duas falhas equivalentes, registre mudança real de método antes de outra tentativa. Pausa ou câmera fixa deliberada não devem virar cauda congelada nem movimento gratuito.',
 'pemara-video-motion-director': 'Para novas sequências live action, use mapa/câmeras/estados compartilhados e teste uma fronteira do bloco piloto. Câmera fixa motivada pode demonstrar a ação interna e a causalidade; não confundir esse caso com freeze, hold ou pose gerada sem progressão. Esta atualização prevalece sobre exigência genérica de translação em todo plano, mantendo contratos específicos de movimento já aprovados. Sem revisão temporal, não emitir parecer positivo de movimento.',
 'image-production': 'Para novas âncoras com atores reais, preservar a fonte antes do primeiro DLSS e usar máscara explícita dos personagens completos. Salvar pelo nó `PemaraSaveActorProtectedImage` ou pelo contrato seletivo, comparando original, intermediário NR e composição. `auto_mask`/controle de pele não excluem atores de forma verificável. Máscara ausente/incompatível bloqueia quando proteção foi solicitada. Não reenviar âncora já artificial como identidade canônica nem tratar duas vezes. Composição técnica de camadas preservadas é acabamento, sem geração procedural de arte nova.',
}
for name, text in blocks.items():
    path = ROOT/'.agents/skills'/name/'SKILL.md'
    current = path.read_text(encoding='utf-8-sig')
    if '## Câmera e preservação dos atores — 2026-10-09' in current:
        raise RuntimeError('Already updated '+name)
    end = current.index('\n---', 4) + len('\n---')
    insertion = '\n\n## Câmera e preservação dos atores — 2026-10-09\n\n'+text+'\n\nLeia `'+REF+'` para schema, evidências, regras de reparo e uso do acabamento seletivo. Essa atualização não autoriza render, muda motor ou reabre mídia entregue.\n'
    path.write_text(current[:end]+insertion+current[end:], encoding='utf-8')

path=ROOT/'.agents/skills/pemara-video-production-lead/references/production-quality-contract.md'
current=path.read_text(encoding='utf-8-sig')
current += '\n## Evidências de câmera e proteção de atores — 2026-10-09\n\nPara novas sequências live action, aplicar [o contrato complementar](camera-evidence-and-actor-protection.md): mapa único, posições/percursos, bloco piloto com fronteira, revisão temporal antes do lote, falhas por método e fontes exatas na montagem. Em novas âncoras com atores, DLSS seletivo com máscara explícita preserva personagens completos. Câmera fixa motivada é válida; não impor translação genérica. Preservar os contratos específicos aprovados. O backend valida evidências, sem inferir qualidade ou aprovação humana.\n'
path.write_text(current,encoding='utf-8')
path=ROOT/'.agents/skills/pemara-video-production-lead/references/review-and-repair.md'
current=path.read_text(encoding='utf-8-sig')
current += '\n## Registro verificável de reparo — 2026-10-09\n\nEm sequências live action, registrar `attempts` por take no contrato de câmera com status, falha, método, arquivo/hash e observação. Duas falhas equivalentes bloqueiam repetir o método: nome novo ou seed diferente não são mudança de estratégia. Conferir o piloto montado antes do restante do lote. Cera/plástico pede comparação da fonte anterior, âncora, SeedVR2 e DLSS para localizar a primeira alteração; proteção no acabamento não desfaz artificialidade já presente na âncora. Ver [contrato complementar](camera-evidence-and-actor-protection.md).\n'
path.write_text(current,encoding='utf-8')
path=ROOT/'AGENTS.md'
current=path.read_text(encoding='utf-8-sig')
prefix='''## Atualização autorizada de câmera e DLSS seletivo — 2026-10-09

Para novas sequências live action com múltiplos planos, usar o contrato complementar em `.agents/skills/pemara-video-production-lead/references/camera-evidence-and-actor-protection.md`: mapa único, estados/câmeras compartilhados, bloco piloto com fronteira e revisão temporal antes do lote. Materializar `sequence_camera_contract.json` na raiz do projeto; o backend valida antes da fila e da montagem. Duas falhas equivalentes exigem mudança real de método. Perfis dos agentes seguem as skills canônicas, sem regras duplicadas.

Em novas âncoras com atores reais, usar DLSS no cenário por composição com máscara explícita, preservando personagens completos da fonte anterior ao primeiro NR. Essa regra atualiza a exigência integral anterior nesse escopo: o DLSS continua executado no intermediário, mas só seu cenário é usado na composição. `skin`/`auto_mask` não substituem a máscara. O perfil seletivo tem recibo próprio, máscara/hash e revisão visual. Proteção solicitada sem máscara válida bloqueia, sem fallback integral. O modo integral histórico e outras mídias permanecem compatíveis. Em vídeo, máscaras precisam acompanhar cada quadro; não repetir máscara de foto. Modo seletivo requer comparação em mídia real antes de alegar qualificação artística.

Câmera fixa dirigida é válida quando sustenta a leitura da ação/reação; não exigir translação em todo plano por uma regra genérica. Contratos específicos de movimento e aspectos aprovados permanecem válidos. Esta atualização não autoriza nova mídia, render de projetos encerrados, alteração de entregas, troca de motor, áudio novo ou reinício sobre trabalhos ativos.

'''
path.write_text(prefix+current,encoding='utf-8')
path=ROOT/'maestro/pemara/services/studio/h3_workflow.py'
current=path.read_text(encoding='utf-8-sig')
old='intencao, sequencia causal, atuacao, fotografia, cobertura, continuidade, cortes e beats 0-30/30-70/70-100; carregar especialistas por fase'
new='mapa unico, cameras/percursos/estados compartilhados, contrato verificavel e bloco piloto com fronteira; intencao, atuacao, cobertura e cortes'
assert current.count(old)==1; current=current.replace(old,new)
old='start frame e end frame quando necessario, com sidecar e elenco conferido nos pixels'
new='ancoras aprovadas por hash, elenco conferido e DLSS seletivo com mascara explicita dos atores; fonte anterior preservada'
assert current.count(old)==1;current=current.replace(old,new)
old='corte cinetico direto entre fontes aprovadas e compativeis; conector causal apenas quando permitido e autorizado; caso contrario corrigir a fonte'
new='fronteiras revisadas em intervalos moveis e geografia compartilhada; corte direto ou acao ausente por conector permitido; fonte incompatível exige correcao'
assert current.count(old)==1;current=current.replace(old,new)
path.write_text(current,encoding='utf-8')
print('Updated 9 skills, 2 shared contracts, AGENTS and H3 catalogue; aliases retained.')
