from change_control import *
import ast
import re
import yaml

# Adopt only inspected concurrent edits; do not erase the music work.
records=json.loads(RECEIPT.read_text(encoding='utf-8'))
adopted=[]
for rel in ['pemara-messenger-turbo/references/turbo_registry.json','pemara-ecosystem-orchestrator/SKILL.md']:
    p=SKILLS/rel; r=records[p.as_posix()]; current=p.read_bytes()
    if digest(current)==r['after_sha256']: continue
    if p.suffix=='.json':
        d=json.loads(read(p)); assert len(d['aliases'])==41 and len(set(d['aliases']))==41 and len(d['specialized_profiles'])==8
        before=json.loads(read(r['backup']))
        additions={'ai-video-intro-pipeline','image-production','creative-director','hero-sprite-scaling','phaser-platformer-architect'}
        assert set(d['aliases'])==set(before['aliases'])|additions
        assert set(d['specialized_profiles'])==set(before['specialized_profiles'])-additions
    else:
        tree=ast.parse(read(BASE/'phase1.py'))
        call=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='skill' and isinstance(n.args[0],ast.Constant) and n.args[0].value=='pemara-ecosystem-orchestrator')
        expected=ast.literal_eval(call.args[2]).strip()
        body=read(p).split('---',2)[2].strip()
        assert body.startswith(expected)
        extra=body[len(expected):].strip()
        assert extra.startswith('## Produção musical — Qwen 3.8') and 'pemara-music-listening-qc' in extra
    checkpoint=BASE/'concurrent_preserved'/rel; checkpoint.parent.mkdir(parents=True,exist_ok=True); checkpoint.write_bytes(current)
    adopted.append({'path':p.as_posix(),'previous_after_sha256':r['after_sha256'],'adopted_sha256':digest(current),'snapshot':checkpoint.as_posix(),'reason':'Reviewed concurrent music append / equivalent registry; preserved without overwrite.'})
    r['after_sha256']=digest(current); r['after_bytes']=len(current)
RECEIPT.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
(BASE/'concurrent_preserved.json').write_text(json.dumps(adopted,ensure_ascii=False,indent=2),encoding='utf-8')

p=SKILLS/'web-frontend-vanilla/SKILL.md'; put(p,read(p).replace('run before reporting complete','apply relevant items before reporting complete').replace('Layout firme de 320px a 1440px','Layout firme nas larguras afetadas; 320px a 1440px quando pertinente'))
p=SKILLS/'audio-analysis/SKILL.md'; t=read(p).replace('print("pico:", float(np.max(np.abs(y))), "(>=1.0 => clipping)")','channels, native_sr = sf.read("audio.wav", always_2d=True)\nprint("picos por canal:", np.max(np.abs(channels), axis=0), "(>=1.0: possível saturação; investigar)")')
t=t.replace('import librosa, numpy as np','import librosa, numpy as np, soundfile as sf',1); put(p,t)
p=SKILLS/'pemara-live-action-showrunner/SKILL.md'; t=read(p)
t=t.replace('dinâmica. Depois do QC integral, selecione e trave por hash uma saída realmente móvel\ndo MP4 como única âncora inicial do take seguinte.', 'dinâmica. Depois do QC integral e da aprovação do take pelo proprietário, proponha uma saída realmente móvel\ndo MP4 como âncora cinética inicial do take seguinte. Registre caminho, hash, função e aprovação exata dessa referência antes do envio; derivar um quadro não concede aprovação canônica automática. A ficha original continua padrão de identidade.')
t=t.replace('três rotas', 'rotas qualificadas no manifest e na tabela abaixo'); put(p,t)
p=SKILLS/'pemara-cinematic-take-director/SKILL.md'; t=read(p)
t=t.replace('Para toda sequência com queda, guerra, desastre, corrupção ou apocalipse, exigir:', 'Para sequências cuja promessa seja destruição ambiental progressiva (colapso, guerra, desastre ou apocalipse), aplicar os itens pertinentes abaixo. Queda corporal comum, duelo e corrupção abstrata não acionam automaticamente este gate. Legenda/narração só são obrigatórias quando pertencem ao tratamento aprovado; dano/escalada devem seguir o arco, sem exigir destruição nova em cada plano:')
t=t.replace('Quando um bloco narrativo precisar de causa e consequência, dividi-lo em dois microtakes curtos com keyframes próprias em vez de comprimir toda a catástrofe numa imagem.', 'Quando um bloco narrativo precisar de causa e consequência, planejar a cobertura necessária conforme a rota e duração qualificadas. Microtakes separados são uma opção editorial, não obrigação que substitua o combate contínuo ou uma tomada aprovada.')
old='''Executar o gate do projeto antes de liberar vídeo:

```powershell
python tools/cinematic_direction_gate.py projeto_video_cutscenes/abertura_fase1/production_manifest.json --takes 01 02
```

Gate vermelho bloqueia GPU.'''
new='''Antes de liberar vídeo, localizar o gate e o manifest reais do projeto e verificar seu schema. `tools/cinematic_direction_gate.py` pertence apenas a projetos que fornecem esse arquivo; não presumir que exista no cwd.

Para manifests de sequência live action compatíveis, o utilitário desta skill é `E:/Pemara/.agents/skills/pemara-cinematic-take-director/scripts/sequence_regression_gate.py`. Consulte `--help`; passe o caminho real do manifest e `--stage contract`, `anchors` ou `assembly` conforme a fase. Não aplicar esse schema a todo vídeo nem preencher caminhos fictícios. O gate específico do contrato qualificado tem precedência. Falha em gate aplicável bloqueia o envio; resultado estrutural não aprova a arte.'''
assert old in t; put(p,t.replace(old,new))

# Correct existing interface metadata while keeping dependencies and policy.
p=SKILLS/'pemara-ecosystem-orchestrator/agents/openai.yaml'; t=read(p)
t=t.replace('Roteia trabalhos entre skills Pemara','Audita e mantém o catálogo de skills Pemara').replace('para escolher as skills certas e montar um plano seguro de execucao Pemara.','para auditar o catálogo, referências e aliases Pemara, preservando requisitos e registrando evidências.'); put(p,t)
for n in json.loads(read(BASE/'metadata_created.json')):
    p=SKILLS/n/'agents/openai.yaml'; d=yaml.safe_load(read(p)); desc=yaml.safe_load(read(SKILLS/n/'SKILL.md').split('---',2)[1])['description'].split('.')[0]
    short=desc if len(desc)<=64 else desc[:65].rsplit(' ',1)[0]
    if len(short)<25: short=d['interface']['short_description']
    line='  short_description: '+json.dumps(short,ensure_ascii=False)
    put(p,re.sub(r'^  short_description:.*$',lambda _:line,read(p),flags=re.M))

p=Path('C:/Users/admin_remoto/.agents/skills/hyperframes/SKILL.md'); t=read(p)
front=t.split('---',2)
front[1]='\nname: hyperframes\ndescription: "Planeja, cria, edita e renderiza composições HTML HyperFrames quando essa stack é escolhida ou já existe no projeto. Inclui motion graphics, decks, montagem e ports solicitados de Remotion. Não substitui motores de vídeo generativo como o H3 do Maestro, Unity ou outra stack existente."\n'
body=front[2]
body=body.replace('# HyperFrames entry point','# HyperFrames entry point\n\n## Escopo local Pemara\n\nPreserve a stack e a versão do projeto. Em pedido somente de plano, entregue o plano/storyboard textual: não executar usage, init, upgrade, render, geração ou instalação como requisito de planejamento. Reaproveite o briefing existente e pergunte apenas pelo que muda a decisão. Não crie `BRIEF.md` dentro da futura pasta de scaffold antes de `init`; mantenha o plano fora dela ou em memória e grave o brief após inicialização autorizada, conforme intent-interview. Para execução, aplique os procedimentos abaixo somente no escopo solicitado; atualização de versão que altere a stack não é automática. Instruções do proprietário prevalecem sobre defaults do pacote.',1)
put(p,'---'+front[1]+'---'+body)

# Public contract regression: the compiled plan must not reintroduce an old
# finisher or new sound generation behind the owner's finishing policy.
p=ROOT/'maestro/pemara/services/studio/test_live_action_workflows.py'; t=read(p)
needle='        self.assertEqual(plan["finishingOrder"][0], "picture_lock")'
replace='''        self.assertEqual(plan["finishingOrder"], [
            "picture_lock", "seedvr2_3b_int8_candidate", "rife_exact60_candidate",
            "dlss5_natural_candidate", "original_audio_stream_copy",
            "technical_qc_and_human_listening", "separate_owner_review",
        ])'''
assert needle in t; put(p,t.replace(needle,replace,1))
print('phase5: independent findings corrected; concurrent music edits preserved')
