"""
sb3_extractor.py
Extrai automaticamente todos os arquivos .sb3 de uma pasta.

.sb3 = ZIP com:
  project.json  — estrutura do projeto (sprites, costumes, sons)
  {md5}.png     — imagens dos sprites
  {md5}.wav     — sons dos sprites
  {md5}.svg     — sprites vetoriais (convertidos para PNG)

Saída:
  organized/{nome_projeto}/{sprite}/{costume}.png
  organized/{nome_projeto}/{sprite}/{som}.wav
  assets_map.json  — atualizado com todos os jogos

Uso:
  python sb3_extractor.py --sb3-dir ./sb3_files --out ./organized
  python sb3_extractor.py --sb3-dir ./sb3_files --out ./organized --map assets_map.json
"""

import json
import zipfile
import shutil
import argparse
import re
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Tenta importar Pillow para converter SVG→PNG e fazer resize
try:
    from PIL import Image
    import io
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("[AVISO] Pillow não instalado — SVGs serão ignorados.")
    print("        pip install Pillow")

# Tenta importar cairosvg para converter SVG
try:
    import cairosvg
    HAS_CAIRO = True
except Exception:
    HAS_CAIRO = False

# ─── Filtros ──────────────────────────────────────────────────────────────────

# Sprites de UI — ignorados para assets_map de personagens
UI_PATTERNS = re.compile(
    r'\b(button|buttons|bar|bars|settings|reset|close|more|preview|'
    r'polo\s*\d*|dark\s*mode|accent|icons?|sprite\d+|leftarrow|'
    r'backdrop|achievement|credit|gallery|mute|background|stage)\b',
    re.IGNORECASE
)

# Sons de UI genéricos — não representam personagem
UI_SOUNDS = {'pop', 'click', 'wrong', 'pop2', 'pop3'}

# Costumes que queremos priorizar (idle first)
IDLE_PATTERNS = re.compile(r'\b(idle|idle\d*|base|default|normal|0)\b', re.IGNORECASE)


def is_ui_sprite(name: str) -> bool:
    return bool(UI_PATTERNS.search(name))


def is_ui_sound(name: str) -> bool:
    return Path(name).stem.lower() in UI_SOUNDS


def clean_name(name: str) -> str:
    """Remove caracteres inválidos para nomes de pasta."""
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip('._')


# ─── Extração de um .sb3 ──────────────────────────────────────────────────────

# ─── Extração de um .sb3 ou Pasta Descompactada ─────────────────────────────────

def _extract_asset(zf: zipfile.ZipFile | None,
                   src_dir: Path | None,
                   asset_index: set[str],
                   asset_meta: dict,
                   dest_dir: Path,
                   dest_name: str) -> Path | None:
    """
    Extrai um asset (costume ou som) do ZIP ou de src_dir para dest_dir/dest_name.ext
    Retorna o Path final ou None se não encontrado.
    """
    md5ext     = asset_meta.get('md5ext', '')
    asset_id   = asset_meta.get('assetId', '')
    data_fmt   = asset_meta.get('dataFormat', 'png').lower()

    # Tenta localizar o arquivo
    candidate = None
    for key in [md5ext, f"{asset_id}.{data_fmt}"]:
        if key in asset_index:
            candidate = key
            break

    if candidate is None:
        return None

    dest_dir.mkdir(parents=True, exist_ok=True)
    ext      = Path(candidate).suffix.lower()
    out_path = dest_dir / f"{dest_name}{ext}"

    # Lê os bytes
    try:
        if zf is not None:
            data = zf.read(candidate)
        elif src_dir is not None:
            with open(src_dir / candidate, 'rb') as f:
                data = f.read()
        else:
            return None
    except Exception:
        return None

    # SVG → PNG se possível
    if ext == '.svg':
        if HAS_CAIRO:
            try:
                png_bytes = cairosvg.svg2png(bytestring=data, output_width=512, output_height=512)
                out_path  = dest_dir / f"{dest_name}.png"
                out_path.write_bytes(png_bytes)
                return out_path
            except Exception:
                pass
        if HAS_PIL:
            try:
                # Fallback: salva SVG mesmo assim
                out_path = dest_dir / f"{dest_name}.svg"
                out_path.write_bytes(data)
                return out_path
            except Exception:
                pass
        return None  # SVG sem conversão disponível

    # Asset binário direto (PNG, WAV, etc.)
    try:
        out_path.write_bytes(data)

        # Valida PNG e converte para RGBA se necessário
        if ext == '.png' and HAS_PIL:
            try:
                with Image.open(io.BytesIO(data)) as img:
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    img.save(out_path, 'PNG')
            except Exception:
                pass  # Mantém o original se falhar

        return out_path
    except Exception:
        return None


def extract_project(sb3_path: Path | None, game_dir: Path | None, out_dir: Path) -> dict | None:
    """
    Extrai um projeto Scratch (.sb3 ou pasta descompactada) e organiza os assets.
    """
    if sb3_path is not None:
        project_name = sb3_path.stem
    elif game_dir is not None:
        project_name = game_dir.name
    else:
        return None

    project_dir  = out_dir / clean_name(project_name)

    zf = None
    src_dir = None
    asset_index = set()
    project = None

    try:
        if sb3_path is not None:
            zf = zipfile.ZipFile(sb3_path, 'r')
            names = zf.namelist()
            asset_index = set(names)
            if 'project.json' not in asset_index:
                print(f"  [SKIP] {sb3_path.name} — sem project.json")
                zf.close()
                return None
            with zf.open('project.json') as f:
                project = json.load(f)
        elif game_dir is not None:
            # Encontra project.json
            found = list(game_dir.rglob("project.json"))
            if not found:
                print(f"  [SKIP] {game_dir.name} — sem project.json")
                return None
            project_json_path = found[0]
            src_dir = project_json_path.parent
            asset_index = {p.name for p in src_dir.iterdir()}
            with open(project_json_path, 'r', encoding='utf-8') as f:
                project = json.load(f)
        else:
            return None

        characters = []
        backgrounds = []

        for target in project.get('targets', []):
            tname     = target.get('name', 'Unknown')
            is_stage  = target.get('isStage', False)
            costumes  = target.get('costumes', [])
            sounds    = target.get('sounds', [])

            if is_stage:
                # Backgrounds
                for c in costumes:
                    img_path = _extract_asset(
                        zf, src_dir, asset_index, c,
                        project_dir / clean_name(tname), 'backdrop'
                    )
                    if img_path:
                        backgrounds.append({
                            'name':  tname,
                            'image': str(img_path),
                            'sound': None,
                        })
                continue

            if is_ui_sprite(tname):
                continue

            # Escolhe melhor costume (idle primeiro, senão o primeiro)
            best_costume = None
            for c in costumes:
                if IDLE_PATTERNS.search(c.get('name', '')):
                    best_costume = c
                    break
            if best_costume is None and costumes:
                best_costume = costumes[0]

            # Extrai imagem
            sprite_dir = project_dir / clean_name(tname)
            img_path   = None
            if best_costume:
                img_path = _extract_asset(zf, src_dir, asset_index, best_costume,
                                          sprite_dir, 'idle')

            # Escolhe melhor som (não-UI)
            best_sound = None
            for s in sounds:
                sname = s.get('name', '')
                if not is_ui_sound(sname):
                    best_sound = s
                    break

            snd_path = None
            if best_sound:
                snd_path = _extract_asset(zf, src_dir, asset_index, best_sound,
                                          sprite_dir, best_sound.get('name', 'sound'))

            if img_path or snd_path:
                characters.append({
                    'name':  tname,
                    'image': str(img_path) if img_path else None,
                    'sound': str(snd_path) if snd_path else None,
                })

    except Exception as e:
        if sb3_path is not None:
            print(f"  [ERRO] {sb3_path.name} — {e}")
        else:
            print(f"  [ERRO] {game_dir.name} — {e}")
        return None
    finally:
        if zf is not None:
            zf.close()

    if not characters and not backgrounds:
        return None

    return {
        'characters':  characters,
        'backgrounds': backgrounds,
    }


def extract_sb3(sb3_path: Path, out_dir: Path) -> dict | None:
    """Interface compatível para trás."""
    return extract_project(sb3_path=sb3_path, game_dir=None, out_dir=out_dir)


# ─── Pipeline principal ───────────────────────────────────────────────────────

def extract_all(sb3_dir: str, out_dir: str, map_path: str,
                workers: int = 4) -> dict:
    """
    Processa todos os .sb3 e pastas descompactadas em sb3_dir em paralelo.
    Retorna o assets_map completo (novo + existente).
    """
    sb3_dir = Path(sb3_dir)
    out_dir = Path(out_dir)
    map_path = Path(map_path)

    sb3_files = sorted(sb3_dir.rglob('*.sb3'))
    
    # Encontra pastas descompactadas sob sb3_dir / "jogos"
    unpacked_dirs = []
    jogos_dir = sb3_dir / "jogos"
    if jogos_dir.exists():
        for d in sorted(jogos_dir.iterdir()):
            if d.is_dir():
                found = list(d.rglob("project.json"))
                if found:
                    unpacked_dirs.append(d)

    total_tasks = len(sb3_files) + len(unpacked_dirs)
    if total_tasks == 0:
        print(f"[AVISO] Nenhum .sb3 ou pasta descompactada em: {sb3_dir}")
        sys.exit(1)

    # Carrega assets_map existente
    assets_map = {}
    if map_path.exists():
        with open(map_path, 'r', encoding='utf-8') as f:
            assets_map = json.load(f)
        print(f"  assets_map existente: {len(assets_map)} jogos")

    print(f"\n{'='*60}")
    print(f"  SB3 Extractor — {total_tasks} projetos ({len(sb3_files)} .sb3, {len(unpacked_dirs)} pastas)")
    print(f"  Saída     : {out_dir}")
    print(f"  Workers   : {workers}")
    print(f"{'='*60}\n")

    new_games   = 0
    total_chars = 0
    errors      = 0

    # Prepara a lista de tarefas: (tipo, path)
    tasks = []
    for p in sb3_files:
        tasks.append(('sb3', p))
    for p in unpacked_dirs:
        tasks.append(('unpacked', p))

    def run_task(task_type, path):
        if task_type == 'sb3':
            return extract_project(sb3_path=path, game_dir=None, out_dir=out_dir)
        else:
            return extract_project(sb3_path=None, game_dir=path, out_dir=out_dir)

    with ThreadPoolExecutor(max_workers=workers) as exe:
        futures = {exe.submit(run_task, t_type, p): (t_type, p) for t_type, p in tasks}

        for i, future in enumerate(as_completed(futures), 1):
            t_type, path = futures[future]
            name = path.name

            try:
                result = future.result()
            except Exception as e:
                print(f"  [{i:3}/{total_tasks}] [ERRO] {name[:50]} — {e}")
                errors += 1
                continue

            if result is None:
                print(f"  [{i:3}/{total_tasks}] [SKIP] {name[:50]} — vazio/ignorado")
                continue

            n_chars = len(result['characters'])
            assets_map[name] = result
            new_games   += 1
            total_chars += n_chars
            print(f"  [{i:3}/{total_tasks}] [OK] {name[:50]}  ({n_chars} personagens)")

    # Salva assets_map atualizado
    with open(map_path, 'w', encoding='utf-8') as f:
        json.dump(assets_map, f, indent=2, ensure_ascii=False)

    print(f"\n{'-'*60}")
    print(f"  Jogos processados : {new_games}")
    print(f"  Total personagens : {total_chars}")
    print(f"  Erros             : {errors}")
    print(f"  assets_map salvo  : {map_path}")
    print(f"{'-'*60}\n")

    return assets_map


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Extrai .sb3 → assets organizados")
    p.add_argument('--sb3-dir', default='.',          help='Pasta com os .sb3')
    p.add_argument('--out',     default='organized',  help='Pasta de saída')
    p.add_argument('--map',     default='assets_map.json', help='assets_map.json')
    p.add_argument('--workers', type=int, default=4,  help='Threads paralelas')
    args = p.parse_args()

    extract_all(args.sb3_dir, args.out, args.map, args.workers)


if __name__ == '__main__':
    main()
