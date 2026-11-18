from change_control import *
import re
import tomllib
import zipfile
import difflib

# Narrow corrections demonstrated by independent behavioral inspection.
p=SKILLS/'web-frontend-vanilla/SKILL.md'; t=read(p)
start=t.index('<!-- ═'); end=t.index('## Princípios',start)
replacement='''## Método e verificação

Leia `E:/Pemara/.agents/skills/pemara-messenger-turbo/references/operating-contract.md` uma vez por contexto. Convenções de log/versionamento vêm do projeto; não impor RULES/FIXLOG/_v2.

Confirme suporte de APIs no alvo. Preserve HTML semântico, foco/teclado, contraste AA, estados hover/focus/disabled/erro, fallback de fontes e degradação sem JS. Verifique telas pequenas, dimensões de mídia/CLS, console e render HTML → CSS → JS. Entregue arquivos reais completos, sem framework novo. Para uma correção localizada, teste o comportamento afetado e a regressão pertinente; testes amplos de responsividade/320–1440px são proporcionais à alteração, não uma segunda auditoria obrigatória para toda edição.

'''
put(p,t[:start]+replacement+t[end:])
p=SKILLS/'audio-analysis/SKILL.md'; t=read(p).replace('Meça, não chute. Instale: `pip install librosa soundfile numpy pyloudnorm` (+ `ffmpeg` no sistema).','Meça, não chute. Primeiro localize o arquivo e as ferramentas já disponíveis. A análise usa librosa/soundfile/numpy/pyloudnorm ou ffmpeg compatíveis; não instalar dependências nem baixar modelos só por carregar esta skill. Use o runtime existente e relate a medição indisponível se faltar uma dependência. Um pedido de análise entrega métricas e interpretação, sem criar música, normalizar, cortar ou sobrescrever a fonte.')
t=t.replace('## Conversão / normalização (ffmpeg)', '## Conversão / normalização (somente quando solicitadas)')
t=t.replace('- Clipping (pico ≥ 1.0 / 0 dBFS) é defeito — reganhe headroom antes de exportar.', '- Pico ≥ 1.0 / 0 dBFS é indício a investigar junto com amostras consecutivas, true peak e escuta; uma amostra no limite não prova clipping audível. Proponha correção se demonstrado; análise não autoriza exportação modificada.')
t=t.replace('## Tom / key (estimativa por chroma)', '## Classe de altura dominante (não determina sozinha o tom/key)')
put(p,t)
p=SKILLS/'pemara-online-security-guardian/SKILL.md'; t=read(p)
t=t.replace('## Fluxo', '## Escopo da revisão\n\nPara revisão de código ou dúvida de isolamento, delimite arquivos, fluxo e testes locais pertinentes. Os passos de validação implantada e recibo de release aplicam-se quando há liberação/implantação no escopo; não exigem acessar produção, instalar scanners ou fazer deploy para responder uma revisão local. Scanners existentes são auxiliares conforme risco e autorização; evidência direta do código e regressão negativa continuam necessárias para o achado.\n\n## Fluxo',1)
put(p,t)

oldroot=Path('C:/Users/admin_remoto/.codex/skills')
newroot=Path('C:/Users/admin_remoto/.agents/skills')
names=['general-video','hyperframes','hyperframes-animation','hyperframes-audio','hyperframes-cli','hyperframes-core','hyperframes-creative','hyperframes-keyframes','hyperframes-registry','media-use']
private=Path('C:/Users/admin_remoto/.codex/backups/skill_consolidation_20261008')
private.mkdir(parents=True,exist_ok=True)
archive=private/'duplicate_skill_sources.zip'
if archive.exists(): raise RuntimeError('Existing archive; inspect before rerun')
sources=[oldroot/n for n in names]+[SKILLS/'saas-pentest-hardening/saas-pentest-hardening']
files=[]
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for source in sources:
        for p in sorted(source.rglob('*')):
            if p.is_file():
                data=p.read_bytes(); label=('user_codex/' if source.parent==oldroot else 'pemara_nested/')+source.name+'/'+p.relative_to(source).as_posix()
                z.writestr(label,data); files.append({'path':p.as_posix(),'archive_member':label,'sha256':digest(data)})
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert all(digest(z.read(r['archive_member']))==r['sha256'] for r in files)

comparisons=[]
for n in names:
    a=oldroot/n/'SKILL.md'; b=newroot/n/'SKILL.md'
    assert a.exists() and b.exists()
    diff='\n'.join(difflib.unified_diff(read(a).splitlines(),read(b).splitlines(),fromfile=a.as_posix(),tofile=b.as_posix(),n=2))
    (BASE/'duplicate_diffs').mkdir(exist_ok=True)
    (BASE/'duplicate_diffs'/f'{n}.diff').write_text(diff,encoding='utf-8')
    comparisons.append({'name':n,'canonical':b.as_posix(),'disabled':a.as_posix(),'canonical_sha256':digest(b.read_bytes()),'disabled_sha256':digest(a.read_bytes())})

# Scoped discovery configuration. Never copy config secrets into the repository.
config=Path('C:/Users/admin_remoto/.codex/config.toml')
original=config.read_bytes(); parsed=tomllib.loads(original.decode('utf-8-sig'))
paths=[(p/'SKILL.md').as_posix() for p in sources]
existing=parsed.get('skills',{}).get('config',[])
assert not any(e.get('path','').replace('\\','/') in paths for e in existing), 'Existing skill overrides require manual merge'
addition='\n# Pemara skill consolidation 2026-10-08: preserved duplicate installations\n'+''.join(f'[[skills.config]]\npath = "{p}"\nenabled = false\n\n' for p in paths)
new=original+addition.encode('utf-8')
after=tomllib.loads(new.decode('utf-8-sig'))
expected=dict(parsed); expected['skills']=dict(parsed.get('skills',{})); expected['skills']['config']=existing+[{'path':p,'enabled':False} for p in paths]
assert after==expected, 'Unexpected config change'
backup=private/'config.toml.before'
assert not backup.exists()
backup.write_bytes(original)
assert config.read_bytes()==original, 'Concurrent config edit'
config.write_bytes(new)
assert tomllib.loads(config.read_text(encoding='utf-8-sig'))==expected
receipt={'source':'https://learn.chatgpt.com/docs/build-skills#enable-or-disable-local-codex-skills','canonical_root':newroot.as_posix(),'reason':'Managed HeyGen HyperFrames installation updated 2026-10-07 in user .agents, with plugin-aware execution paths and current reference layout; old .codex copy preserved as historical compatibility source. Nested SaaS methods linked by canonical parent.','config_backup_private':backup.as_posix(),'config_before_sha256':digest(original),'config_after_sha256':digest(new),'app_restart_required':True,'active_discovery_after_restart_verified':False,'disabled_paths':paths,'archive':archive.as_posix(),'archive_sha256':digest(archive.read_bytes()),'files':files,'comparisons':comparisons}
(BASE/'discovery_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('phase4: 11 duplicate discovery entries disabled; files preserved and archive verified; app restart pending')
