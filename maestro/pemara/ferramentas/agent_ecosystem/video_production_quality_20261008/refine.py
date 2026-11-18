from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path('E:/Pemara')
HERE = Path(__file__).resolve().parent
manifest = json.loads((HERE/'source_before.json').read_text(encoding='utf-8'))

for rel in ['.agents/skills/ai-video-intro-pipeline/SKILL.md', '.agents/profiles/ai-video-intro-pipeline.md']:
    path = ROOT/rel
    backup = HERE/'source_before'/rel
    if backup.exists():
        raise RuntimeError(f'Backup already exists: {backup}')
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert hashlib.sha256(backup.read_bytes()).hexdigest() == digest
    manifest.append({'path': str(path), 'backup': str(backup), 'sha256_before': digest})

    text = path.read_text(encoding='utf-8-sig')
    title_end = text.index('\n\n', text.index('\n# '))
    text = text[:title_end]+'''\n\n## Direção e acabamento vigentes

Usar `pemara-video-production-lead` para intenção/produção, `pemara-cinematography-director` para fotografia, `pemara-performance-director` quando houver personagens e `pemara-film-editor` para ritmo/montagem. Carregar por fase, sem criação automática de subagentes.

O Maestro usa MiniMax H3 com Sage + Spectrum, sem LTX ou troca automática para provedor externo. As regras de slides ambientais/anime abaixo são específicas da intro Ritmos da Revolta quando esse brief as exigir; não proíbem elenco ou impõem anime a outras produções. Preservar versão/identidade e estilo do pedido atual.

Revisar o MP4 inteiro, atuação/ação, fotografia, identidade, geografia e ritmo, além de contatos/junções e técnica. Contact sheet não comprova movimento. Som novo, geração, registro e publicação dependem do escopo; fonte silenciosa não ganha música/Foley por padrão. Não reabrir projetos encerrados.
'''+text[title_end:]
    text = text.replace('4. Monte primeiro um preview sem audio temporario. Audio ruim mascara erro visual e torna o diagnostico confuso.',
                        '4. Revise a leitura visual sem som quando útil, silenciando o player. Preserve o áudio existente; proxy video-only exige decisão de edição e não substitui a fonte.')
    text = text.replace('5. So depois de aprovar visualmente, aplique musica, SFX, logo oficial, normalizacao, export final e FHD.',
                        '5. Depois da aprovação visual/picture lock, aplicar somente música/SFX/mix/logo já autorizados; acabamento segue SeedVR2 3B → RIFE exato 60 → DLSS 5, preservando áudio. Cada alteração continua candidata.')
    text = text.replace('- Preview visual deve ser video-only quando a trilha final ainda nao esta fechada.',
                        '- Inspeção visual pode silenciar o player; preserve o áudio original. Não remover faixa da fonte nem incorporar trilha nova sem escopo autorizado.')
    start = text.index('## FHD e upscale')
    end = text.index('## Registro e rastreabilidade', start)
    text = text[:start]+'''## FHD e upscale

Depois da fonte/picture lock aprovados, usar `E:/Pemara/maestro/pemara/services/studio/upscaling_required.py`: SeedVR2 3B int8 → RIFE 4.25 j/60 → DLSS 5 Natural, copiando o áudio existente. Preservar nativo, candidato e recibos/hashes. Scale/unsharp não substitui esse workflow. Não gerar Foley para fonte silenciosa nem contratar enhancer externo automaticamente.

Entrega de arquivo não significa publicação. Disponibilizar somente as versões solicitadas e identificar o estado de revisão do artefato exato. Registro do projeto preserva fontes/histórico; pacote final usa hashes dos arquivos efetivamente aprovados.

'''+text[end:]
    start = text.index('## Práticas 2026')
    end = text.index('## Verificacao minima', start)
    text = text[:start]+'''## Direção executável

- Duração vem dos beats úteis e da grade qualificada; contratos específicos, como FFVIII V8 e combate contínuo, prevalecem sobre exemplos de clipes modulares.
- Não trocar para modelo barato/caro para testar por hábito. Usar um segmento representativo dentro do motor, controles e orçamento autorizados antes de repetir o lote.
- Texto/logo exatos vêm de composição determinística e assets oficiais. Elementos proibidos de um slide ambiental não são restrições universais do elenco de outros projetos.
- Edição técnica e codecs usam `video-production`; correção começa pela causa na fonte, sem emenda para disfarçar falha.

'''+text[end:]
    text = text.replace('Use comandos equivalentes aos do projeto:',
                        'Exemplos históricos da intro Ritmos da Revolta: usar somente se pertencem ao projeto atual e o render/registro já estiver autorizado. Não executar render por uma atualização de agentes:')
    path.write_text(text, encoding='utf-8')

(HERE/'source_before.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

path = ROOT/'.agents/skills/pemara-video-motion-director/SKILL.md'
text = path.read_text(encoding='utf-8')
text = text.replace('- the take adds humans, bodies, faces, eyes, or humanoid silhouettes.',
                    '- the take adds unrequested characters, changes cast count, or invents anatomy;\n- an environmental-only take adds humans, bodies, faces, eyes or humanoid silhouettes forbidden by its specific brief. These prohibitions do not exclude the approved cast in an acting scene.')
text = text.replace('   - animated light, particles, or object transformation.',
                    '   - a visible response from the environment or another scene element, without forcing particles, flashes or transformation into every scene.')
text = text.replace('Particles/light: [visible change].',
                    'Environment/secondary response: [causal visible change, no decorative effect required].')
extracted = []
for start_marker, end_marker, pointer in [
    ('## Universal Transition Motion Gate', '## High-Energy Combat Gate',
     'Before every I2V/T2V take or transition, read the full Universal Transition Motion Gate in\n`references/motion-quality-gates.md`. Preserve all four pillars, active beats and compatible\nkinetic cuts; generated connectors require permission from the route and scope.'),
    ('## High-Energy Combat Gate', '## Engine and Runtime Admission',
     'For combat, long action, transformation or fragile anatomy/count, read the full High-Energy\nCombat Gate in `references/motion-quality-gates.md` and use `pemara-live-action-combat-director`.\nSpecific start-only controls take precedence over generic intermediate-anchor suggestions.')]:
    start, end = text.index(start_marker), text.index(end_marker)
    extracted.append(text[start:end].strip())
    text = text[:start]+start_marker+'\n\n'+pointer+'\n\n'+text[end:]
(path.parent/'references/motion-quality-gates.md').write_text(
    '# Motion and action gates\n\nRequired operational reference, loaded by phase. Current AGENTS and route-specific contracts prevail.\n\n'+
    '\n\n'.join(extracted)+'\n', encoding='utf-8')
path.write_text(text, encoding='utf-8')

path = ROOT/'.agents/skills/pemara-cinematic-take-director/SKILL.md'
text = path.read_text(encoding='utf-8')
text = text.replace('- keyframes aprovadas de início/fim e, em cenas longas, intermediárias.',
                    '- keyframes aprovadas conforme o modo qualificado; start-only não recebe destino final ou intermediário por uma regra genérica.')
text = text.replace('estratégia de controle — por exemplo, usar múltiplas âncoras ou microtrechos — em vez de repetir o\nmesmo prompt integral.',
                    'estratégia de controle qualificada — ajustar staging, densidade de eventos ou âncoras/microtrechos\nquando permitidos pela rota — em vez de repetir o mesmo prompt integral.')
path.write_text(text, encoding='utf-8')

print('Refinados escopo ambiental, âncoras por rota, intro especializada e referências progressivas.')
