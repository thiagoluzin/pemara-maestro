"""Install scoped musical production roles and preserve edited routing files."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path('E:/Pemara')
HERE = Path(__file__).resolve().parent
BACKUP = HERE / 'routing_before'
CONTRACT = '''# Contrato de produção musical

Qwen 3.8 é o coordenador musical local escolhido pelo proprietário. Na criação automática,
define letra original, idioma, estilo, BPM proposto, duração e arco por seções. Letra fornecida,
duração manual, motor e instrumental explicitamente escolhido são imutáveis. Na reinstrumentação,
planeja a produção; não reescreve letra, cantor, notas protegidas, andamento da fonte ou duração.

## Ordem do trabalho

1. Identificar criação original ou adaptação. Fixar intenção, motor, fonte, instrumentos, voz e limites.
2. Fonte de cover: preservar bytes/hash e inspecionar duração/codec; preferir stems e partitura corrigida.
3. Qwen propõe plano validado em JSON com papéis, ganhos, energia e solista por seção. Sem análise
   musical fornecida, marcadores são propostas. Qwen textual não escuta áudio nem mede BPM.
4. MuScriptor é rascunho; comparar MIDI/prova A/B com a gravação. Revisão do proprietário fixa hash.
5. Voz: stem fornecido alinhado ou Demucs local. Ouvir segunda voz, sílabas, reverb, sibilantes,
   vazamento instrumental e sincronismo. Igualdade de duração não comprova alinhamento musical.
   Hash bloqueia o asset vocal revisado; separação não recupera necessariamente o stem verdadeiro.
6. Renderizar pistas independentes. Contrato MIDI protege notas/ataques/durações. Novas camadas de
   acompanhamento devem ter contrato próprio; não usar base generativa para substituir a referência.
7. Qwen controla ganhos e pequenos contrastes suaves por seção. Notas protegidas não são apagadas
   para produzir pausas. Voz preservada não recebe essa automação; master tem processamento próprio.
8. Checar WAV e MP3 finais: decode, taxa/canais, duração, amostras não finitas, clipping e true peak
   até -1 dBTP. LUFS informa escuta; não é uma nota artística nem meta universal de volume.
9. Ouvir música integral e trechos críticos; avaliar separadamente identidade, canto, timbre,
   arranjo, dinâmica, mix e finalização. Candidato tecnicamente rejeitado não pode ser promovido.

## Direção e revisão

Registro de crítica: tempo → defeito ouvido → efeito musical → pista/causa → correção proposta.
Comparar A/B com volume de escuta equivalente, voz solo, base solo e mix completa. Dar prioridade
ao canto e ao hook; versos com espaço, refrões com contraste e transições com causa musical.
Não mascarar instrumentos com guitarra contínua, confundir MIDI duplicado com duas performances,
ou chamar soundfont de guitarra gravada. DI FreePats é um instrumento amostrado com saturação/EQ;
a cadeia leve não equivale a amplificador capturado nem garante articulação real de palm mute.

## Limites e qualificação

ACE-Step cover é experimental: pode variar melodia/voz. MuQ/MERT ajudam a comparar e diagnosticar,
mas similaridade não prova cópia fiel. BS-RoFormer/Mel-Band e modos ACE lego/complete são extensões
a qualificar por checkpoint/configuração/licença e referência; não escolher automaticamente.
Não prometer 100% de fidelidade a um mix. Hash de asset e igualdade MIDI são provas limitadas.
Original, tentativas rejeitadas e histórico são preservados. Instalar skills não autoriza render,
publicação, compra, serviço pago, troca de motor ou treino. Codex opera ComfyUI exclusivamente
pelo MCP; backend Maestro permanece autônomo. TypeSafe obrigatório mantém o Qwen escolhido
e validação determinística; nenhuma chamada paga por mera presença desta skill.

Implementação: E:/Pemara/maestro/pemara/services/studio/music_qwen.py, music_writer.py,
music_score_first.py, music_vocals.py, music_delivery.py e music_ai_audio.py.
'''

ROLES = {
 'pemara-music-production-lead': ('Produção musical', 'Coordena criação, covers e qualidade musical local',
    'Use para dirigir a produção musical completa do Maestro, coordenar Qwen 3.8, organizar criação original ou cover e corrigir falta de qualidade.',
    'Feche objetivo, referência, motor e identidade antes do arranjo. Use Qwen para o plano, arranjador para a execução e engenharia para mix/master. Priorize os problemas ouvidos e mantenha o piloto pendente de escuta. Nunca aprove artisticamente por score técnico.'),
 'pemara-music-arranger': ('Arranjo musical', 'Dirige forma, instrumentação e identidade do cover',
    'Use para reinstrumentação, mudança de gênero, preservação de melodia/harmonia/voz, forma musical e arranjo por pistas.',
    'Separe identidade fixada e acompanhamento permitido. Revise partitura contra áudio, não apenas contra outro MIDI. Organize riffs, baixo, bateria e contrapontos em torno da voz; evite dobrar a melodia em todos os instrumentos. Marque articulações disponíveis e limites reais do instrumento. Preserve tempo variável e caudas.'),
 'pemara-music-mix-engineer': ('Engenharia de mix', 'Equilibra pistas e verifica áudio e entrega final',
    'Use para mix, masterização, headroom, clipping, true peak, loudness, vazamento vocal, mascaramento e problemas de áudio do Maestro.',
    'Comece por stems e dinâmica. Ouça voz, base e mix; examine mascaramento, transientes, região grave, imagem estéreo e fadiga. Não tentar reparar clipping existente apenas reduzindo ganho. Valide master e arquivo codificado real. Registro de medidas não substitui escuta.'),
 'pemara-music-listening-qc': ('Revisão musical', 'Revisa identidade e produção com evidência de escuta',
    'Use para avaliar canção criada, cover ou reinstrumentação, revisar letra/voz, identidade, timbres, arranjo, mix e final musical.',
    'Avalie fonte e candidato integralmente. Faça comparação em volume equivalente e registre defeitos com timestamp. Diferencie nota errada na transcrição, timbre artificial, voz vazando e erro de mix. Relate o que foi realmente ouvido e o que está sem evidência. Aprovação pertence ao proprietário; sugestão do Qwen ou métricas não a substituem.'),
}

changes = []
def write(path, content):
    old = path.read_bytes() if path.exists() else None
    if old is not None:
        backup = BACKUP / path.relative_to(ROOT)
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists(): shutil.copy2(path, backup)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    changes.append({'path': str(path), 'sha256Before': hashlib.sha256(old).hexdigest() if old else None,
                    'sha256After': hashlib.sha256(path.read_bytes()).hexdigest()})

for name, (title, short, description, instructions) in ROLES.items():
    path = ROOT / '.agents/skills' / name
    write(path / 'SKILL.md', f'''---
name: {name}
description: {description}
---

# {title}

{instructions}

Leia o [contrato de produção musical](../pemara-music-production-lead/references/music-production-contract.md)
antes de atuar. Respeite TypeSafe, a stack e as escolhas explícitas do proprietário.
Esses agentes são papéis; não crie subagentes sem autorização específica.
''')
    write(path / 'agents/openai.yaml', f'''interface:
  display_name: "{title}"
  short_description: "{short}"
  default_prompt: "Use ${name} para melhorar a produção musical do Maestro com o Qwen 3.8."
policy:
  allow_implicit_invocation: true
''')
write(ROOT / '.agents/skills/pemara-music-production-lead/references/music-production-contract.md', CONTRACT)
registry_path = ROOT / '.agents/skills/pemara-messenger-turbo/references/turbo_registry.json'
registry = json.loads(registry_path.read_text(encoding='utf-8-sig'))
registry['aliases'] = sorted(set(registry['aliases']) | set(ROLES))
write(registry_path, json.dumps(registry, ensure_ascii=False, indent=2) + '\n')
route = '''\n## Produção musical — Qwen 3.8\n\nComece com `pemara-music-production-lead`; use `pemara-music-arranger`,
`pemara-music-mix-engineer` e `pemara-music-listening-qc` conforme a fase.
Qwen 3.8 é o coordenador local de letra, duração escolhida pelo modelo, estilo e plano de produção.
Na adaptação, preserve fonte, canto e identidade musical. Plano textual e QC técnico não aprovam
qualidade artística. Esses papéis não autorizam subagentes, nova mídia ou troca de motor.\n'''
for relative in ('.agents/profiles/agents-turbo.md', '.agents/skills/pemara-messenger-turbo/SKILL.md',
                 '.agents/skills/pemara-ecosystem-orchestrator/SKILL.md',
                 '.agents/README_PEMARA_ECOSYSTEM.md', 'AGENTS.md'):
    p = ROOT / relative
    text = p.read_text(encoding='utf-8-sig')
    if '## Produção musical — Qwen 3.8' not in text: write(p, text.rstrip() + '\n' + route)
p = ROOT / '.agents/skills/pemara-ecosystem-orchestrator/scripts/skill_inventory.ps1'
text = p.read_text(encoding='utf-8-sig')
if '"pemara-music-production-lead"' not in text:
    text = text.replace('  "pemara-video-production-lead",',
        '  "pemara-video-production-lead",\n' + ''.join(f'  "{name}",\n' for name in ROLES))
    write(p, text)
(HERE / 'skill_changes.json').write_text(json.dumps(changes, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'skills': list(ROLES), 'editedOrCreatedFiles': len(changes)}, ensure_ascii=False))
