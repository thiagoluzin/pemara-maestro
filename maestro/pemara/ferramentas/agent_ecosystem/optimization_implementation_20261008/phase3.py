from change_control import *
import re
import subprocess
import sys
import yaml

# Resolve dangling references found during validation using the criteria already
# present in the consolidated family, rather than inventing missing libraries.
for p in [SKILLS/'project-planner/SKILL.md', SKILLS/'project-planner/references/task-breakdown.md']:
    t=read(p).replace('Referência existente `E:/Pemara/.agents/skills/planning-and-task-breakdown/references/definition-of-done.md`, quando aplicável', 'Aceite por tarefa, verificações afetadas e evidência real em [task-breakdown.md](references/task-breakdown.md)')
    t=t.replace('Para critérios gerais de conclusão, a referência de apoio existente é `E:/Pemara/.agents/skills/planning-and-task-breakdown/references/definition-of-done.md`. Critérios específicos do projeto prevalecem.', 'Conclusão exige aceite atendido, verificações afetadas executadas e evidência registrada. Critérios específicos do projeto prevalecem; documento preenchido não comprova execução.')
    put(p,t)
p=SKILLS/'performance-optimizer/references/measurement.md'
put(p,read(p).replace(' Para checklists adicionais, consulte `E:/Pemara/.agents/skills/performance-optimization/references/performance-checklist.md` somente nas seções aplicáveis; métricas do projeto prevalecem.',' Métricas e critérios de aceite do projeto prevalecem.'))

for n in ['phaser-platformer-architect','phaser-16bit-platformer']:
    p=SKILLS/n/'SKILL.md'
    put(p,read(p)+'''\n## Verificação da especialidade\n\nConfirme APIs em `phaser.d.ts` da versão instalada. Investigue delta no retorno de aba, tunneling, input no mesmo frame, deadzone, pixels fracionários e latência de áudio. Trace input → estado → velocidade → física → colisão → câmera → render. Buffer, coyote e salto variável formam um sistema; entidades transitórias devem ter ciclo de vida/pool apropriado. Entregue cenas completas e valide desempenho no alvo, escala inteira, colisão e feel em playtest. Não declare feel aprovado por headless. Defina resolução interna, Arcade/Matter, origem do mapa e plataforma quando afetarem arquitetura.\n''')

# Keep this registered specialization, but route common recipes to the skill.
p=PROFILES/'phaser-16bit-platformer.md'
front=read(p).split('---',2)[1]
put(p,'---'+front+'---\n\n# Especialização Phaser 16-bit\n\nLeia `E:/Pemara/.agents/skills/phaser-16bit-platformer/SKILL.md` e as referências da receita necessária. Este perfil mantém o foco em implementação Phaser 3 de plataforma 16-bit; confirme a versão instalada antes de aplicar. A arquitetura/feel vem de `phaser-platformer-architect`. Não manter uma segunda cópia de snippets ou fatos de versão neste perfil. Preserve motor, gênero e critérios do projeto.\n')

p=PROFILES/'agents-turbo.md'
put(p,read(p).replace('Antes de concluir, execute o auditor do Messenger Turbo e o inventário do ecossistema Pemara. Relate aliases, especializações preservadas, erros e skills realmente usadas.', 'Ao modificar o catálogo, aliases ou roteamento, execute o auditor do Messenger Turbo e o inventário do ecossistema Pemara. Nas demais tarefas, execute somente as verificações pertinentes ao trabalho, sem repetir auditoria de catálogo inalterado.'))

p=ROOT/'maestro/pemara/ferramentas/video_global_engine/workflows/minimax_h3_live_action/manifest.json'
d=json.loads(read(p)); d['finishingOrder']=['picture_lock','seedvr2_3b_int8_candidate','rife_exact60_candidate','dlss5_natural_candidate','original_audio_stream_copy','technical_qc_and_human_listening','separate_owner_review']
d['finishingContract']='services/studio/upscaling_required.py'
put(p,json.dumps(d,ensure_ascii=False,indent=2)+'\n')
p=SKILLS/'pemara-live-action-combat-director/agents/openai.yaml'
put(p,read(p).replace('transformar esta luta em microtakes com golpes assinatura, física e efeitos pertencentes ao personagem correto.', 'dirigir a sequência de luta pela rota H3 qualificada, com intenção, defesa ativa, contato e consequência física, preservando identidade e duração do contrato.'))
p=SKILLS/'pemara-live-action-combat-director/SKILL.md'
t=read(p).replace('contrato por microtake','contrato por take da rota escolhida').replace('- O defensor não inicia voo, queda ou recuo antes do quadro de contato visível.', '- A resposta involuntária ao impacto (voo, queda ou recuo causado pelo golpe) não precede o contato. Esquiva, bloqueio, passo de defesa e contra-ação motivados pela leitura do atacante podem começar antes; cada evento precisa declarar sua causa.')
t += '\nO campo legado `defenderMotionBeforeContactForbidden` continua obrigatório para compatibilidade com o compilador; expressa a proibição de resposta ao impacto antes da causa, não a imobilização do defensor. Não altere o schema de produções históricas. Declare defesas antecipatórias separadamente no ledger e revise sua causalidade no MP4. A geometria do perfil `h3_approved_action_720p8s` é 1280×720; outros perfis Hero/Master usam 1344×768. Confirme o perfil resolvido no plano; não confundir as rotas.\n'
put(p,t)
p=SKILLS/'pemara-live-action-showrunner/SKILL.md'
t=read(p).replace('| Luta com golpes, armas ou poderes próprios de personagens | `h3_live_action_signature_combat` | FL2VA |','| Gesto isolado, arma ou pose icônica | `h3_live_action_signature_combat` | FL2VA |\n| Luta bilateral contínua | `h3_live_action_continuous_bilateral_combat_8s` | FL2VA; start-only qualificada quando aplicável |')
t=t.replace('- `critical`: Master, `1344x768 / 20 steps / 24 fps`, com âncora intermediária quando houver ação.', '- `critical`: Master, `1344x768 / 20 steps / 24 fps` nas rotas isoladas compatíveis. Combate bilateral de oito segundos usa o perfil específico 1280×720/20 passos/24 fps e proíbe âncora intermediária; a rota start-only usa apenas a inicial.')
t=t.replace('Story contract e microtakes conectados por causa', 'Story contract e takes da rota escolhida conectados por causa')
put(p,t)

# Fold the unique imported security methods into the canonical entry without
# moving or deleting the original package or its seven reference files.
p=SKILLS/'saas-pentest-hardening/SKILL.md'
refs=sorted((p.parent/'saas-pentest-hardening/references').glob('*.md'))
put(p,read(p)+'\n## Referências por classe\n\nAntes da correção, leia o método da classe pertinente; os exemplos devem ser adaptados à stack e à versão reais. O pacote importado fica preservado como biblioteca, com sua entrada duplicada desativada.\n\n'+''.join(f'- [{r.stem}](saas-pentest-hardening/references/{r.name})\n' for r in refs)+'\nCada achado liga evidência → exploração controlada → correção → detecção sugerida. Classifique pelo impacto demonstrado, registre pontos seguros sem inventar falhas e priorize por severidade/esforço. Detecção sugerida não autoriza instalar monitor. Examine encadeamentos entre auth, IDOR e mass assignment; use autorização no servidor, schemas de entrada, atomicidade, mínima exposição e tenant/RLS conforme a arquitetura.\n')

# Current navigation, with the historical document retained by the receipt.
put(ROOT/'PEMARA_PROJECT_MAP.md','''# Mapa atual Pemara — 2026-10-08

Entrada operacional: [Messenger Turbo](.agents/skills/pemara-messenger-turbo/SKILL.md).
Seleção por fase: [mapa canônico](.agents/skills/pemara-messenger-turbo/references/routing-map.md).
Regras do proprietário: [AGENTS.md](AGENTS.md), com precedência das ordens mais recentes.

Vídeo começa por `pemara-video-production-lead`; combate, atuação, fotografia, montagem, continuidade e QC permanecem especialistas distintos. Música começa por `pemara-music-production-lead`. Manutenção do catálogo usa `pemara-ecosystem-orchestrator`.

Maestro gera novos vídeos somente com MiniMax H3, Sage + Spectrum, sem fallback. O acabamento vigente é o contrato `maestro/pemara/services/studio/upscaling_required.py`. Regras antigas de Wan, LTX e FPS não regem novas produções. Mídias/projetos históricos permanecem preservados.

Mapa anterior, histórico sem autoridade operacional: [snapshot preservado](maestro/pemara/ferramentas/agent_ecosystem/optimization_implementation_20261008/source_before/pemara/PEMARA_PROJECT_MAP.md).
Implementação e verificação: [relatório](maestro/pemara/ferramentas/agent_ecosystem/optimization_implementation_20261008/LEIA_ME.md).
''')
put(SKILLS/'pemara-ecosystem-orchestrator/references/pemara-skill-map.md','''# Catálogo e encaminhamento Pemara

O mapa operacional único é [routing-map.md](../../pemara-messenger-turbo/references/routing-map.md). Não duplicar sua árvore aqui.

O registro de perfis está em [turbo_registry.json](../../pemara-messenger-turbo/references/turbo_registry.json). O inventário curado é `../scripts/skill_inventory.ps1`; presença em disco não comprova descoberta ou capacidade executável.

Para manutenção: inventariar → comparar requisitos → backup/hash → alteração delimitada → validar registro, referências e comportamento → recibo. Gates de evidência Maestro estão em [maestro-evidence.md](maestro-evidence.md). Políticas e autorizações vigentes vêm do AGENTS do projeto, sem duplicação neste catálogo.
''')
put(ROOT/'.agents/README_PEMARA_ECOSYSTEM.md','''# Ecossistema Pemara

Use [Messenger Turbo](skills/pemara-messenger-turbo/SKILL.md) como entrada de seleção; [mapa de responsabilidades](skills/pemara-messenger-turbo/references/routing-map.md) como fonte única por fase. `agents-turbo` é compatibilidade; `pemara-ecosystem-orchestrator` mantém o catálogo.

Registro atual: 41 aliases e oito especializações, além do dispatcher. Os quatro especialistas recentes de música estão preservados. Papéis não obrigam criação de subagentes.

Vídeo começa por `pemara-video-production-lead`; a direção de combate preserva atuação, fotografia, montagem, continuidade e QC separados. O método comum está em [operating-contract.md](skills/pemara-messenger-turbo/references/operating-contract.md). Planejamento, depuração e performance possuem uma entrada canônica por família e módulos condicionais.

Auditoria: [recomendações aprovadas](../maestro/pemara/ferramentas/agent_ecosystem/optimization_audit_20261008/RECOMENDACOES.md).
Alterações, backups e verificações: [implementação](../maestro/pemara/ferramentas/agent_ecosystem/optimization_implementation_20261008/LEIA_ME.md).
''')

# Generate new UI metadata with the bundled creator, only for curated skills and
# the three consolidated compatibility entrypoints. Existing metadata survives.
inventory=read(SKILLS/'pemara-ecosystem-orchestrator/scripts/skill_inventory.ps1').split('$pemaraSkills = @(',1)[1].split(')',1)[0]
names=re.findall(r'"([a-z0-9-]+)"',inventory)+['spec-driven-development','planning-and-task-breakdown','debugging-and-error-recovery','performance-optimization']
created=[]
for name in sorted(set(names)):
    target=SKILLS/name/'agents/openai.yaml'
    if target.exists(): continue
    stage=BASE/'metadata_staging'/name
    stage.mkdir(parents=True,exist_ok=True)
    desc=yaml.safe_load(read(SKILLS/name/'SKILL.md').split('---',2)[1])['description']
    short=desc.split('.')[0][:64].rstrip()
    if len(short)<25: short='Especialista Pemara: '+name
    args=[sys.executable,'-B','C:/Users/admin_remoto/.codex/skills/.system/skill-creator/scripts/generate_openai_yaml.py',str(stage),'--name',name,'--interface','short_description='+short,'--interface',f'default_prompt=Use ${name} para atender este pedido no projeto e na stack existentes, com evidências e escopo preservados.']
    cp=subprocess.run(args,capture_output=True,text=True,encoding='utf-8')
    if cp.returncode: raise RuntimeError(cp.stdout+cp.stderr)
    put(target,(stage/'agents/openai.yaml').read_bytes()); created.append(name)
(BASE/'metadata_created.json').write_text(json.dumps(created,indent=2),encoding='utf-8')
print('phase3: current video policy, navigation, security references and metadata updated; new metadata:',len(created))
