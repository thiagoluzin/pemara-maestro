from pathlib import Path
import json
import hashlib

ROOT = Path('E:/Pemara')
SKILLS = ROOT / '.agents/skills'
HERE = Path(__file__).resolve().parent
CONTRACT = 'E:/Pemara/.agents/skills/pemara-video-production-lead/references/production-quality-contract.md'
changes = []

def read(rel):
    return (ROOT/rel).read_text(encoding='utf-8-sig')

def write(rel, content):
    path = ROOT/rel
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.read_bytes() if path.exists() else None
    path.write_text(content, encoding='utf-8')
    changes.append({'path': str(path), 'sha256_before': hashlib.sha256(old).hexdigest() if old is not None else None,
                    'sha256_after': hashlib.sha256(path.read_bytes()).hexdigest()})

def replace(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError(f'Expected one occurrence, found {text.count(old)}: {old[:90]}')
    return text.replace(old, new)

def skill(name, addition):
    rel = f'.agents/skills/{name}/SKILL.md'
    text = read(rel)
    title_end = text.index('\n\n', text.index('\n# '))
    text = text[:title_end] + '\n\n' + addition.strip() + text[title_end:]
    write(rel, text)

names = ['pemara-video-production-lead', 'pemara-cinematography-director',
         'pemara-performance-director', 'pemara-film-editor']
rel = '.agents/skills/pemara-messenger-turbo/references/turbo_registry.json'
registry = json.loads(read(rel))
registry['aliases'] = sorted(set(registry['aliases'] + names))
write(rel, json.dumps(registry, ensure_ascii=False, indent=2)+'\n')

rel = '.agents/skills/pemara-ecosystem-orchestrator/scripts/skill_inventory.ps1'
text = read(rel)
text = replace(text, '  "pemara-cinematic-take-director",',
               '  "pemara-cinematic-take-director",\n'+''.join(f'  "{name}",\n' for name in names)+
               '  "pemara-live-action-combat-director",\n  "pemara-live-action-kinetic-supervisor",')
write(rel, text)

skill('pemara-messenger-turbo', '''## Produção de vídeo — rota vigente

Pedido para criar, melhorar ou corrigir a qualidade de um vídeo começa com `pemara-video-production-lead`, que fecha a sequência e direciona as fases. Atuação: `pemara-performance-director`; fotografia: `pemara-cinematography-director`; montagem: `pemara-film-editor`. Esses papéis não exigem subagentes. Carregue no máximo três skills primárias por fase, além dos gates obrigatórios, trocando o conjunto conforme o trabalho avança.

O Maestro usa MiniMax H3; LTX foi removido pelo proprietário. Não escolher motor/provedor alternativo. Acabamento atual: SeedVR2 3B int8 → RIFE 4.25 j/60 → DLSS 5 Natural com áudio existente copiado. As políticas antigas de motor/acabamento em referências históricas não são instrução para novas produções.''')
skill('pemara-ecosystem-orchestrator', '''## Video production routing

Use `pemara-video-production-lead` for the complete production and quality review. Route acting to `pemara-performance-director`, image design to `pemara-cinematography-director`, and narrative assembly to `pemara-film-editor`. Work in phases with at most three primary skills at a time. These are responsibilities; do not spawn agents merely because profiles exist.

For Maestro, preserve the current H3-only route, Sage + Spectrum, and approved SeedVR2 3B → exact RIFE60 → DLSS 5 finishing with existing audio. Current owner instructions supersede older engine or finishing notes.''')

rel = '.agents/profiles/agents-turbo.md'
text = read(rel)
text += '''\n## Vídeo\n\nComece com `pemara-video-production-lead` para produção/qualidade; selecione `pemara-performance-director`, `pemara-cinematography-director` ou `pemara-film-editor` pelo risco da fase. Use os especialistas de combate, continuidade, voz e QC quando necessários. Papéis não são autorização para criar subagentes. Preserve fontes, motor H3, Sage + Spectrum e acabamento obrigatório vigente.\n'''
write(rel, text)

rel = '.agents/README_PEMARA_ECOSYSTEM.md'
text = read(rel)
text = replace(text, '## Regra de video\n\nVideo profissional deve ser feito por takes:\n\n1. Direcao criativa.\n2. Imagem-base/keyframe aprovado.\n3. JSON/descritivo fiel da imagem.\n4. Prompt de movimento com camera, parallax e evento.\n5. Geracao de take curto.\n6. QC visual e tecnico.\n7. Montagem final.', '''## Regra de video — revisão 2026-10-08

Começar por [pemara-video-production-lead](skills/pemara-video-production-lead/SKILL.md). Planejar a experiência do público, a sequência e cada take antes do prompt. Atuação, fotografia, identidade, ação e montagem precisam de decisões próprias e revisão do arquivo real.

| Agente/skill | Responsabilidade |
|---|---|
| `pemara-video-production-lead` | produção completa, roteiro visual, riscos e correções |
| `pemara-cinematography-director` | composição, blocking, câmera motivada, luz e geografia |
| `pemara-performance-director` | intenção, escuta, gesto, peso, reação e recuperação |
| `pemara-film-editor` | seleção, ritmo, cobertura, cortes e revisão da sequência |

São papéis sequenciais, sem obrigação de criar subagentes. O roteador mantém no máximo três skills primárias por fase. Os especialistas existentes de combate, continuidade, movimento, voz e QC continuam responsáveis pelos seus gates.

Fluxo: intenção → sequência/identidade → direção de atuação e fotografia → âncoras aprovadas → contrato executável → geração autorizada → revisão integral dos takes → aprovação exata das fontes → montagem/revisão do filme → picture lock aprovado → acabamento obrigatório → nova avaliação.

Maestro: MiniMax H3 com Sage + Spectrum, sem LTX/fallback. Acabamento: SeedVR2 3B int8 → RIFE 4.25 exato 60 FPS → DLSS 5 Natural com cópia do áudio existente. Não reabrir projetos históricos nem gerar por uma atualização de skills. Completar plano ou testes não aprova qualidade artística.

Revisão comum: [contrato de qualidade](skills/pemara-video-production-lead/references/production-quality-contract.md). Histórico da atualização: `E:/Pemara/maestro/pemara/ferramentas/agent_ecosystem/video_production_quality_20261008/LEIA_ME.md`.''')
write(rel, text)

rel = 'AGENTS.md'
text = read(rel)
heading = '## Produção de vídeo: agentes e skills - 2026-10-08\n\n'
section = '''Para novos pedidos de criação, direção, melhoria ou revisão de vídeos, começar com `E:/Pemara/.agents/skills/pemara-video-production-lead/SKILL.md`. Dirigir a sequência antes do prompt e carregar atuação (`pemara-performance-director`), fotografia (`pemara-cinematography-director`) e montagem (`pemara-film-editor`) conforme a fase. Manter os especialistas existentes de combate, continuidade, movimento, voz e QC.

Esses são papéis que um mesmo agente pode executar; não exigem subagentes. Planejamento completo e testes técnicos não comprovam qualidade artística. Revisar os arquivos reais com evidências temporais e preservar a aprovação exata do proprietário, os aspectos aprovados, o motor H3 com Sage + Spectrum e o acabamento obrigatório. Atualização de método não autoriza render ou reabertura de projetos encerrados.

'''
first_heading = text.index('\n## ')
text = text[:first_heading]+'\n\n'+heading+section+text[first_heading+1:]
write(rel, text)

rel = '.agents/skills/pemara-video-motion-director/SKILL.md'
text = read(rel)
text = replace(text, 'description: Direction, anchor-faithful prompting, research, QC, and regeneration workflow for Pemara generative video projects. Use when planning or improving image-to-video takes with MiniMax H3 or LTX 2.5, prompt motion, camera movement, approved compatibility IC-LoRAs, keyframe validation, ComfyUI outputs, or Ritmos da Revolta intro generation.',
               'description: "Direção de movimento, beats, controles, âncoras e QC temporal de vídeos Pemara. Use para takes MiniMax H3 no Maestro, ação física, câmera, cauda estática, continuidade cinética e correção de movimento; preservar motor e regras vigentes."')
text = replace(text, 'There is no active default GPU window for video. Treat video generation/training as blocked unless the user explicitly opens a new window.',
               'Honor the current owner authorization, pause flags and actual GPU/queue state. Do not treat an old scheduling note as a permanent ban or assume that an empty queue means free VRAM. This skill does not authorize generation by itself.')
text = replace(text, '''Permanent engine contract: every boundary uses a generated continuous-action connector or remains
inside one uninterrupted take. Crossfade/xfade, freeze frames, holds, static tails, motion resets
and occlusion used to hide a motion swap are forbidden. The connector must inherit visible body,
object, effect and camera velocity, execute one irreversible action, and hand visible motion into
the next take.''', '''Use a DIRECT_KINETIC_CUT between approved, compatible moving sources, remain within one
uninterrupted take, or use a generated continuous-action connector only when the route permits
it and the scope authorizes it. generatedConnectorAllowed: false forbids all generated bridges.
Crossfade/xfade, freeze frames, holds, static tails, motion resets and occlusion used to hide a
motion swap are forbidden. A permitted connector must inherit body, object, effect and camera
velocity, execute a causal irreversible action and deliver useful motion to the next take.''')
start = text.index('The user\'s selected video engine is locked for the take.')
end = text.index('Before every GPU batch', start)
text = text[:start]+'''For Maestro production, preserve MiniMax H3, the current owner-selected route after LTX removal
on 2026-10-08. Do not reinstall LTX, compatibility IC-LoRAs or offer any alternate-engine fallback.
Require SageAttention + Spectrum effectively connected to sampling and preserve the qualified
profile, geometry, frames and audio. See references/model-research.md for the current contract.
Historical research outside Maestro does not change its active production engine.

'''+text[end:]
text = replace(text, 'For human or humanoid acting in the Maestro, keep the selected H3 or LTX 2.5 engine and use approved',
               'For human or humanoid acting in the Maestro, keep MiniMax H3 and use approved')
start = text.index('There is no ranking between H3 and LTX 2.5 in the Maestro.')
end = text.index('## Motion Prompt Pattern', start)
text = text[:start]+'''Maestro uses H3; other engines belong only to separately authorized research. Verify live node/model
support through MCP before any authorized generation. More anchors are not always better: preserve
the start-only combat route when future anchors caused anticipation or static tails. Do not train
or add a video LoRA as an automatic answer to weak direction.

'''+text[end:]
text = replace(text, '6. Default to 3–5 seconds for one action plus reaction. Allow 6–10 seconds only when the direction contract proves multiple distinct events and a changed final state.',
               '6. Choose duration from the directed beats and qualified frame grid. The specific continuous-combat eight-second contract takes precedence over a generic 3–5 second suggestion; do not shorten or extend an approved route automatically.')
title_end = text.index('\n\n', text.index('\n# '))
text = text[:title_end]+'''\n\n## Production handoff

Receive the sequence and take brief from `pemara-video-production-lead`, acting from
`pemara-performance-director` and geography/camera from `pemara-cinematography-director`.
Translate those decisions to controls and motion; do not invent additional actions, change
identity or hide poor performance with camera movement. Record stimulus, contact, response,
support and useful exit intervals in the actual MP4. See the shared production-quality-contract
for independent review dimensions. A detector score never establishes artistic quality.
'''+text[title_end:]
write(rel, text)

write('.agents/skills/pemara-video-motion-director/references/model-research.md', '''# Current Maestro video engine contract — 2026-10-08

The current owner order removed LTX and its exclusive assets. MiniMax H3 is the production choice;
there is no LTX compatibility-asset exception or alternate-engine fallback for new Maestro jobs.
Historical research and delivered media remain preserved, without reinstall or automatic migration.

## MiniMax H3

Read `E:/Pemara/maestro/pemara/services/studio/h3_workflow.py` and the chosen live-action workflow
for the actual supported mode/profile/frame grid. Preserve explicit settings. Require SageAttention
plus Spectrum in sampling, using `h3_spectrum_master20.json`; do not stack FirstBlockCache.

Start with MCP `comfyui-local` server_info. Verify the actual runtime, nodes, queue, VRAM and pauses,
then validate the exact graph via MCP before authorized generation. Disk inventory is not live
capacity, and a built JSON does not authorize queue submission. Maestro's own backend remains autonomous.

Use approved anchors and typed continuity states; do not describe Ref2VA as exact mocap. If end or
intermediate anchors caused early reactions/frozen tails in continuous combat, use the qualified
start-only route rather than endlessly varying seed under the same failing constraint.

## Finishing

Approved native source/picture lock → SeedVR2 3B int8 → RIFE 4.25 j/60 → DLSS 5 Natural → candidate,
copying existing audio. Follow `services/studio/upscaling_required.py`, preserve native/receipt/hash,
and require review of the exact finished artifact. No automatic Foley on silent sources.

## Research isolation

Other engines require a separate explicit owner decision and qualified integration. This document
is not an install instruction or model ranking. No version, download, training or provider change
is authorized by reading it. See the current AGENTS for priorities and approval limits.
''')

rel = '.agents/skills/pemara-live-action-qc/SKILL.md'
text = read(rel)
text = replace(text, 'Ordem fixa: picture lock → RIFE 60 fps candidato → Foley por blocos → QC quantitativo e escuta humana → master audiovisual imutável aprovado → Real-ESRGAN FHD candidato → nova revisão humana.',
               'Ordem vigente: fonte/picture lock aprovados → SeedVR2 3B int8 → RIFE 4.25 exato 60 FPS em timestamps j/60 → DLSS 5 Natural → candidato com cópia do áudio existente → nova revisão humana. Usar `E:/Pemara/maestro/pemara/services/studio/upscaling_required.py`. Não criar Foley para fonte silenciosa nem substituir o contrato por Real-ESRGAN. Preservar recibos/hashes e conferir herança para não tratar duas vezes.')
write(rel, text)
skill('pemara-live-action-qc', f'''## Revisão artística completa

Leia `{CONTRACT}` para registrar evidência por dimensão. Além de identidade, física e técnica, avaliar história/clareza, atuação, fotografia, ritmo e som disponível. Assistir ao MP4 completo, conferir contatos e junções densamente e ouvir o áudio real; se não houver acesso temporal/escuta, deixar esses itens `PENDING`.

Não confundir o rótulo `PASS_TECHNICAL_PENDING_HUMAN_REVIEW` com passe artístico. Uma dimensão artística `FAIL` bloqueia seleção mesmo com decode perfeito. `PASS` do agente precisa de observações e timestamps; aprovação do proprietário exige evidência do artefato exato. `NOT_APPLICABLE` precisa de motivo, nunca serve para ignorar uma falha.

Para cada defeito, entregar intervalo, observação, efeito na cena, hipótese de causa, correção prioritária e aspectos aprovados preservados. Não exigir nova geração por uma inspeção retrospectiva de projeto encerrado. Não calcular nota média que compense identidade ou causalidade falha.''')

rel = '.agents/skills/pemara-live-action-showrunner/SKILL.md'
text = read(rel)
text = replace(text, '8. Conectores em movimento e picture lock.\n9. RIFE, Foley, aprovação audiovisual e upscale, sempre como passes reversíveis.',
               '8. Cortes cinéticos diretos entre fontes aprovadas; conectores causais somente quando permitidos e autorizados. Revisão da montagem inteira e picture lock humano.\n9. SeedVR2 3B int8 → RIFE 4.25 em j/60 → DLSS 5 Natural, copiando o áudio existente, preservando nativo/recibos e submetendo o acabado à revisão própria. Não criar Foley por padrão.')
text = replace(text, '7. QC técnico do MP4 e aprovação humana do artefato exato.',
               '7. Revisão do MP4 completo por história, atuação, fotografia, identidade, ação/física e continuidade, além do QC técnico; aprovação humana do artefato exato.')
write(rel, text)
skill('pemara-live-action-showrunner', '''## Integração de produção

Receba do `pemara-video-production-lead` a sequência, a curva de tensão e as fichas dos takes. Feche atuação com `pemara-performance-director` e geografia/fotografia com `pemara-cinematography-director` antes de compilar. O operador não decide a dramaturgia durante o render.

Toda geração H3 exige SageAttention + Spectrum conectados ao caminho de amostragem, conforme o contrato vigente; indisponibilidade bloqueia sem trocar motor. Perfis abaixo são restrições técnicas, não garantia artística nem autorização para elevar custo automaticamente. A rota específica de combate contínuo prevalece sobre durações/âncoras genéricas.''')

skill('pemara-live-action-combat-director', '''## Intenção e leitura do combate

Receba o arco da sequência da produção. Cada troca precisa de objetivo, tentativa, defesa/contra-ação e mudança de iniciativa. A tática deve revelar personalidade e informação nova, sem adicionar golpes só para preencher duração.

Com `pemara-performance-director`, dirija olhar, leitura do adversário, esforço, reação e recuperação. Com `pemara-cinematography-director`, mantenha base e linha de ataque/contato legíveis. Clarão, som ou corte não substituem contato. O editor recebe vetores e fases de ação, não apenas poses bonitas.

O contrato de oito segundos abaixo é específico. Se âncoras futuras causarem reação antecipada ou congelamento em duas tentativas, aplicar a rota start-only qualificada de `pemara-live-action-showrunner`; não insistir em duas âncoras por uma regra genérica. Corrigir o método, mantendo H3, identidade e aspectos aprovados. Acabamento segue o AGENTS vigente, sem Foley novo por padrão.''')
rel = '.agents/skills/pemara-live-action-combat-director/SKILL.md'
text = read(rel)
text = replace(text, 'Use exatamente duas âncoras ImageGen aprovadas e vinculadas por hash:',
               'Na rota FL2VA de duas âncoras, use exatamente duas imagens aprovadas e vinculadas por hash; a rota start-only qualificada, quando aplicável, exige somente a inicial:')
write(rel, text)

skill('pemara-live-action-continuity', '''## Continuidade de intenção e estado

Além do vetor físico, preservar o que cada personagem sabe, procura, teme e acabou de perceber. Um corte pode manter a pose e perder a reação ou a iniciativa; compare os beats da produção e a partitura de atuação.

Entregar ao `pemara-film-editor` intervalos úteis, estado cinético e motivo de junção. Campos de ação irreversível dentro do conector aplicam-se apenas quando existe conector permitido; corte direto não exige gerar uma ponte. O quadro propagado preserva pose/movimento; rosto, materiais e proporções continuam comparados com a ficha original.

Não pedir conector automaticamente para toda fronteira. Falha de identidade, física ou geografia exige fonte corrigida. Repetição de dano desaparecendo não se resolve por transição editorial.''')
skill('pemara-live-action-kinetic-supervisor', '''## Fronteiras no filme completo

Receba da produção os beats e do editor os intervalos reais escolhidos. Compare movimento antes/depois do corte, estímulo/resposta, intenção, iniciativa e estado ambiental. Similaridade de pose não garante velocidade ou causalidade.

Registre observações com timestamps e frame de contato/reação quando disponíveis; não invente medida física ou escore decimal. Entregue separadamente compatibilidade cinética, falhas de identidade e falhas de atuação/fotografia para os especialistas; um canal não compensa outro. A montagem completa também precisa ser revista.

O método não cria áudio nem autoriza geração de emendas. H3 permanece com Sage + Spectrum, acabamento e aprovação exata seguem o AGENTS atual.''')
skill('pemara-voice-performance-director', '''## Atuação vocal dentro da cena

Receba de `pemara-performance-director` o interlocutor, objetivo da fala, subtexto, estímulo e virada. Dirija uma ação por frase — convencer, esconder, interromper, proteger — e marque onde a percepção muda a entrega. Não usar o mesmo grito ou intensidade em toda fala.

Confronte a duração efetiva da voz com os beats do corpo e com o editor, sem cortar fonemas, congelar personagem ou alterar o picture lock para acomodar fala não planejada. Escuta, pausa e respiração precisam servir à cena. Avaliar voz sozinha e no contexto disponível, com evidência do arquivo real; silêncio dirigido permanece silêncio.

O motor vocal e o texto aprovados permanecem; planejar interpretação não autoriza nova voz/clonagem/áudio. Acabamento de vídeo copia o áudio existente; mudança de mix/voz exige escopo próprio e revisão da candidata.''')

rel = '.agents/skills/pemara-cinematic-take-director/SKILL.md'
text = read(rel)
text = replace(text, 'especialmente no Maestro, MiniMax H3, Wan, LTX, FramePack e ComfyUI.',
               'especialmente no Maestro com MiniMax H3 e ComfyUI, preservando os contratos específicos.')
text = replace(text, '''Contrato permanente do motor: toda fronteira usa um conector de acao gerado ou permanece dentro
de um take unico ininterrupto. Crossfade/xfade, freeze frame, hold, cauda estatica, reset de pose e
oclusao usada para esconder troca de movimento sao proibidos. O conector herda velocidades
visiveis de corpo, objetos, efeitos e camera, executa uma acao irreversivel e termina entregando
movimento ao take seguinte.''', '''Toda fronteira deve usar corte cinetico direto entre fontes aprovadas e compativeis, permanecer
dentro de take ininterrupto ou usar conector causal somente quando a rota permitir e o escopo
autorizar. `generatedConnectorAllowed: false` bloqueia emendas geradas. Crossfade/xfade, freeze,
hold, cauda estatica, reset e oclusao para esconder troca de movimento sao proibidos. Um conector
permitido herda vetores de corpo, objetos, efeitos e camera, progride e entrega movimento util.''')
text = replace(text, '''Marcar `identity_risk: high` ou `critical` quando houver elenco parecido, anatomia frágil, contagem
exata, mudança de forma ou ação longa. Esses takes exigem âncoras intermediárias aprovadas e hashes
vinculados aos beats; uma única âncora não é evidência suficiente.''', '''Marcar `identity_risk: high` ou `critical` quando houver elenco parecido, anatomia frágil, contagem
exata, mudança de forma ou ação longa. Planejar controles e evidência reforçados conforme a rota.
Âncoras intermediárias aprovadas são úteis em transformação/pose técnica quando qualificadas;
combate contínuo start-only não pode recebê-las por regra genérica. A ficha original, o bloco fixo
de identidade e o QC temporal continuam obrigatórios; uma âncora isolada não prova fidelidade.''')
text = replace(text, 'Escolher a menor duração que comunica o beat:',
               'Escolher a duração que comunica o beat na grade do modo qualificado. A tabela é uma referência editorial; o contrato específico de combate contínuo de oito segundos prevalece. Não encurtar ou estender fontes aprovadas automaticamente:')
write(rel, text)
skill('pemara-cinematic-take-director', f'''## Direção de produção integrada

Receba tratamento e sequência de `pemara-video-production-lead`. Feche atuação jogável e fotografia antes do prompt: objetivo/obstáculo, estímulo e reação; ponto de vista, blocking, trajetória de câmera, luz e material. Entregue ao editor a informação e o vetor que motivam o corte.

Leia `{CONTRACT}` para a ficha do take e a revisão por dimensões. Um take deve satisfazer intenção, atuação, fotografia, identidade e ritmo, além de movimento e técnica. Sem vídeo observado, não registrar qualidade como verificada. Preserve o H3 com Sage + Spectrum e o acabamento SeedVR2 3B → RIFE exato 60 → DLSS 5, com áudio existente.''')

# Move conditional, long gate text intact to a progressively loaded reference.
rel = '.agents/skills/pemara-cinematic-take-director/SKILL.md'
text = read(rel)
sections = [
    ('## Intenção de publicação na internet', '## Sala de direção obrigatória',
     'Quando o pedido atual indicar publicação na internet, ler integralmente a seção **Intenção de publicação na internet** em `references/production-gates.md` antes de roteiro/âncoras. O gatilho não autoriza publicar ou gerar.'),
    ('## Padrão canônico live action do Maestro', '## Regra antirremendo',
     'Para produção live action, ler integralmente as seções de padrão canônico, arte, identidade e foto aprovada em `references/production-gates.md`, além de `references/vejito-liveaction-standard.md`. Preservar gates por estágio, referências imutáveis e parecer independente por dimensão.'),
    ('## Gate universal de transicoes', '## Contrato de take',
     'Antes de qualquer take/transição I2V/T2V, ler integralmente **Gate universal de transicoes** em `references/production-gates.md`. Manter os quatro pilares e os beats ativos; corte cinético direto é válido quando comprovadamente compatível. Contratos específicos e direção explícita prevalecem.')]
extracted = []
for start_marker, end_marker, pointer in sections:
    start, end = text.index(start_marker), text.index(end_marker)
    extracted.append(text[start:end].strip())
    text = text[:start]+start_marker+'\n\n'+pointer+'\n\n'+text[end:]
write('.agents/skills/pemara-cinematic-take-director/references/production-gates.md',
      '# Gates de produção e publicação\n\nTexto operacional extraído da skill para leitura por etapa; não é histórico opcional. O AGENTS e o contrato específico vigente prevalecem.\n\n'+'\n\n'.join(extracted)+'\n')
write(rel, text)

rel = '.agents/skills/pemara-cinematic-take-director/references/vejito-liveaction-standard.md'
text = read(rel)
text = replace(text, '# Padrão canônico live action do Maestro: Vejito', '''# Padrão canônico live action do Maestro: Vejito

## Prioridade atual — 2026-10-08

Herdar o método artístico e as aprovações exatas, não os antigos motores/passes. Para novas produções, H3 exige Sage + Spectrum; o acabamento vigente é SeedVR2 3B int8 → RIFE 4.25 j/60 → DLSS 5 Natural com cópia do áudio existente. Foley novo requer escopo explícito. As ordens de passes antigas descritas abaixo são histórico do projeto, não instrução para substituírem o AGENTS atual.

Mais âncoras não são regra universal: em combate contínuo, a rota start-only qualificada prevalece quando controles futuros causaram reação antecipada ou cauda estática. Preservar identidade pela ficha original, bloco fixo e QC temporal.''')
text = replace(text, '9. Fazer Foley depois do picture lock, com aprovação humana de escuta separada.',
               '9. Preservar o áudio aprovado; quando houver pedido específico de Foley novo, fazê-lo depois do picture lock e exigir escuta humana separada. Acabamento novo segue o AGENTS vigente.')
text = replace(text, '''4. **Risco alto exige múltiplas âncoras:** elenco parecido, contagem exata, transformação, apêndices
   frágeis e combate longo recebem keyframes intermediárias aprovadas.''', '''4. **Risco alto exige controle e QC reforçados:** transformação e pose técnica podem receber
   keyframes intermediárias aprovadas conforme a rota; combate contínuo start-only não recebe
   guias futuras por uma regra genérica. Conferir ficha, anatomia e estados em todos os beats.''')
text = replace(text, '''- `identity_contract` em cada take, com elenco esperado/proibido, traços obrigatórios/proibidos e
  `identity_risk`; riscos `high`/`critical` exigem `internal_anchors` aprovadas;''', '''- `identity_contract` em cada take, com elenco esperado/proibido, traços obrigatórios/proibidos e
  `identity_risk`; controles e `internal_anchors`, quando aplicáveis, seguem a rota qualificada.
  Se um gate antigo exigir guia incompatível com start-only, reportar o conflito e corrigir o
  contrato/gate antes do envio; não falsificar âncora nem bypassar validação;''')
write(rel, text)

for rel in ['.agents/skills/creative-director/SKILL.md', '.agents/profiles/creative-director.md']:
    text = read(rel)
    text += '''\n## Direção de vídeo integrada — 2026-10-08

Para produção de vídeo, usar `pemara-video-production-lead` como coordenação; este especialista fecha conceito e tratamento. Atuação, fotografia e montagem passam às skills próprias conforme a fase. A recomendação genérica de duração não substitui contratos específicos, como combate contínuo de oito segundos.

Defina a sensação/intenção e a prova visual, não uma coleção de adjetivos. Em educação, separar objetivo pedagógico da produção; em publicidade, ligar promessa à demonstração real. Preservar todas as regras de jogos acima, sem aplicar fun-core/MVP a um vídeo que não seja jogo.

No Maestro, usar H3 com Sage + Spectrum, sem LTX/fallback. Acabamento vigente: SeedVR2 3B int8 → RIFE exato 60 → DLSS 5 Natural com áudio existente copiado. Ordem histórica de Vejito não muda esse contrato. Concepção não autoriza geração nem reabertura de projeto encerrado.\n'''
    write(rel, text)

video = '''---
name: video-production
description: "Executa produção e edição técnica de vídeo: inspeção ffprobe/decode, corte, concat, texto gráfico, legendas, áudio autorizado, codecs e integridade. Use para montar, editar, diagnosticar ou entregar arquivos de vídeo; direção artística passa pelo production lead. Intro de jogo com marca usa ai-video-intro-pipeline."
---

# Video Production — execução e integridade

Receba direção de `pemara-video-production-lead` e tabela de montagem de `pemara-film-editor`. Transforme decisões em edição reproduzível, sem decidir dramaturgia, trocar motor ou alterar fontes aprovadas silenciosamente. Completar testes não significa aprovação artística.

<!-- TURBO ENGINE v2 — DO NOT REMOVE -->
## Protocolo de execução

1. Leia AGENTS/spec vigentes, verifique autorização, arquivos, hashes, aprovação exata e restrições da rota. Preserve originais, rejeitados e versões. Não reabrir projeto encerrado.
2. Inspecione os arquivos reais: ffprobe, decode, duração, FPS, frames, codec, cor, resolução e todas as faixas de áudio. Não anunciar que mediu algo só porque o comando está pronto.
3. Compare a tabela de montagem com fontes aprovadas: in/out reais, grade de frames, direção de tela e estados de entrada/saída. Rejeitados não entram como 'melhores trechos'.
4. Não normalizar tudo por hábito. Incompatibilidade de FPS, geometria, cor ou áudio requer decisão explícita e solução qualificada; stream copy somente com bitstreams compatíveis. Preserve o áudio existente.
5. Para filtros complexos já autorizados, verificar um segmento representativo antes do lote, sem promover esse teste. Execução Comfy pelo Codex é exclusivamente MCP `comfyui-local`, com inventário vivo e validação do grafo exato; o backend Maestro mantém seu canal autônomo.
6. Execute sem ocultar exit code. Registre comando, parâmetros, fonte/hash, saída/hash, recibos e alterações em registro do projeto. Não imprimir credenciais.
7. Faça decode e medição da saída completa; revisar visualmente o MP4, contatos/junções e o áudio real quando houver. Contact sheet não basta para afirmar movimento, naturalidade ou sincronismo.
8. Mantenha independentes: integridade técnica, parecer artístico e aprovação do proprietário. Sem acesso temporal/escuta, registre a limitação e os itens pendentes.
<!-- End TURBO ENGINE v2 -->

## Motor, processamento e acabamento

No Maestro, MiniMax H3 é a escolha vigente depois da remoção do LTX. H3 exige SageAttention + Spectrum no caminho de amostragem. Não reinstalar LTX nem oferecer motor alternativo. Fora do Maestro, preserve a stack/motor expressamente escolhidos; esta skill não recomenda contratação ou mudança automática de provedor.

Após aprovação da fonte/picture lock, novos acabamentos de vídeo seguem `E:/Pemara/maestro/pemara/services/studio/upscaling_required.py`: **SeedVR2 3B int8 → RIFE 4.25 em j/60 → DLSS 5 Natural**, copiando áudio existente. Usar perfis aprovados FHD/QHD/UHD, preservar nativo e recibos com hashes. Não criar áudio para fonte silenciosa. DLSS válido herdado evita tratamento duplicado em cópia/mux/proxy/concat; geometria ou bitstream alterado precisa da qualificação do contrato.

Scale/unsharp/Real-ESRGAN não substituem esse acabamento. Nunca alterar duração, corte, transparência, profundidade/cor ou faixas silenciosamente para passar o gate. RIFE não corrige coreografia ou identidade. V8 específico de FFVIII prevalece sobre permissões genéricas de trim/retime.

Usar caminho GPU qualificado para render/encode; para entrega FFmpeg, NVENC conforme política vigente. Indisponibilidade não autoriza fallback CPU/libx264. Stream copy/mux e inspeção leve são CPU permitida. Sem GPU autorizada, preparar comandos e relatórios sem executá-los.

## Comandos de inspeção e operações sem troca criativa

Exemplos para adaptar aos caminhos medidos e ao escopo autorizado; não são comprovação de execução:

```powershell
ffprobe -v error -show_format -show_streams -of json "fonte.mp4"
ffmpeg -v error -i "fonte.mp4" -map 0:v:0 -map 0:a? -f null -
# Concat somente após conferir compatibilidade e aprovação de todas as fontes:
ffmpeg -f concat -safe 0 -i "lista_aprovada.txt" -map 0:v:0 -map 0:a? -c copy "montagem_candidata.mp4"
# Prancha INTERNA para localizar aparência/tempos; não comprova movimento:
ffmpeg -i "fonte.mp4" -vf "select=not(mod(n\\,48)),scale=320:-1,tile=6x5" -frames:v 1 -update 1 "qc_interno.jpg"
```

Tabela de corte usa timestamps/frame counts reais; não usar `-shortest` para esconder truncamento nem `-an` para perder áudio. Inspeção silenciosa significa silenciar o player, não remover a faixa da fonte.

Mix/nivelamento só quando autorizado: medir antes/depois, definir alvo pelo destino/spec, preservar voz/Foley aprovados e ouvir o resultado. Um alvo LUFS genérico não comprova qualidade nem autoriza modificar uma trilha aceita. Texto/logo exatos devem vir de assets autorizados/composição determinística, sem depender de texto inventado pelo gerador.

## Saída e revisão

Entregue arquivo candidato com link local absoluto, hashes, comando/recibo, comparação de duração/FPS/frames/áudio e falhas/pendências. Não sobrescrever master. Antes de entregar visual novo, exigir acabamento DLSS vigente e o recibo; registrar herança quando aplicável.

Use `E:/Pemara/.agents/skills/pemara-video-production-lead/references/production-quality-contract.md` para a revisão artística; papel técnico não pode declarar que o filme ficou bom apenas por codec/FPS/decode. Aprovação final e publicação são decisões separadas.

Intro/cutscene de jogo com logo/registro mantém `ai-video-intro-pipeline`. Identidade recorrente, combate, movimento e voz carregam seus gates específicos; não transferir regras de um tipo de vídeo para todos os demais.
'''
write('.agents/skills/video-production/SKILL.md', video)
write('.agents/profiles/video-production.md', video+'''\n## Especialização deste perfil: operador de montagem

Este perfil especializado recebe a tabela editorial já decidida e cuida de conformidade, concat/encode, legendas, mix autorizado e integridade. Divergência de in/out, referência, geografia ou aprovação volta ao editor/diretor antes de executar. A skill canônica cobre a produção técnica geral; este perfil não assume concepção do filme. Manter registrado como especialização no Messenger Turbo, sem criar agentes adicionais por padrão.\n''')

# Correct stale UI suggestions while preserving any policy/dependency blocks.
rel = '.agents/skills/pemara-video-motion-director/agents/openai.yaml'
text = read(rel)
for line in text.splitlines():
    if line.strip().startswith('default_prompt:'):
        text = replace(text, line, '  default_prompt: "Use $pemara-video-motion-director para dirigir movimento e revisar takes MiniMax H3 no Maestro, preservando identidade, ação, motor e aprovação exata."')
    elif line.strip().startswith('short_description:'):
        text = replace(text, line, '  short_description: "Direção de movimento e QC temporal de takes H3"')
write(rel, text)

(HERE/'integration_changes.json').write_text(json.dumps(changes, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Integração concluída: {len(changes)} operações locais. Sem execução de mídia ou runtime.')
