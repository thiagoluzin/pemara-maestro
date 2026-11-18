"""
pipeline.py
Orquestrador completo — roda todo o pipeline de uma vez.

Etapas:
  1. EXTRACT   — extrai .sb3 → organized/ + atualiza assets_map.json
  2. DB        — constrói sprunki.db com todos os personagens
  3. SLICE     — auto_slicer → static/icons/ + parts_index.json
  4. LORA      — prepara dataset de treino

Uso rápido (tudo):
  python pipeline.py --sb3-dir ./sb3_files

Etapas individuais:
  python pipeline.py --sb3-dir ./sb3_files --only extract
  python pipeline.py --only db
  python pipeline.py --only slice
  python pipeline.py --only lora

Flags úteis:
  --workers 8          paralelismo na extração
  --preview            salva imagens de debug do slicer
  --no-rembg           pula remoção de fundo no dataset LoRA
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

# ─── Utilitários ─────────────────────────────────────────────────────────────

def banner(title: str) -> None:
    w = 60
    print(f"\n{'═'*w}")
    pad = (w - len(title) - 2) // 2
    print(f"{'═'*pad} {title} {'═'*(w - pad - len(title) - 2)}")
    print(f"{'═'*w}\n")


def run_step(label: str, cmd: list[str], fatal: bool = True) -> bool:
    """Executa um subcomando e exibe output em tempo real."""
    banner(label)
    print(f"  $ {' '.join(str(c) for c in cmd)}\n")
    t0 = time.time()

    result = subprocess.run(cmd, text=True)
    elapsed = time.time() - t0

    if result.returncode != 0:
        print(f"\n  [ERRO] {label} falhou (código {result.returncode}) — {elapsed:.1f}s")
        if fatal:
            sys.exit(result.returncode)
        return False

    print(f"\n  ✓ {label} concluído em {elapsed:.1f}s")
    return True


def check_file(path: str, label: str) -> bool:
    if not Path(path).exists():
        print(f"  [SKIP] {label} — arquivo não encontrado: {path}")
        return False
    return True


# ─── Pipeline ────────────────────────────────────────────────────────────────

def run_pipeline(args) -> None:
    only = args.only  # None = tudo

    steps_done  = []
    steps_skip  = []
    t_total     = time.time()

    # ── 1. EXTRACT ──────────────────────────────────────────────────────────
    if only in (None, 'extract'):
        sb3_dir = Path(args.sb3_dir)
        if not sb3_dir.exists():
            print(f"[ERRO] --sb3-dir não existe: {sb3_dir}")
            sys.exit(1)

        sb3_count = len(list(sb3_dir.rglob('*.sb3')))
        if sb3_count == 0:
            print(f"[AVISO] Nenhum .sb3 em {sb3_dir} — pulando extração.")
            steps_skip.append('extract')
        else:
            cmd = [
                sys.executable, 'sb3_extractor.py',
                '--sb3-dir', str(sb3_dir),
                '--out',     args.out_organized,
                '--map',     args.assets_map,
                '--workers', str(args.workers),
            ]
            ok = run_step(f'EXTRACT ({sb3_count} arquivos .sb3)', cmd)
            (steps_done if ok else steps_skip).append('extract')
    else:
        steps_skip.append('extract')

    # ── 2. DB ────────────────────────────────────────────────────────────────
    if only in (None, 'db'):
        if not check_file(args.assets_map, 'DB'):
            steps_skip.append('db')
        else:
            cmd = [
                sys.executable, 'sprunki_db_builder.py',
                '--assets', args.assets_map,
                '--db',     args.db_path,
                '--export-json', 'sprunki_summary.json',
                '--no-colors',   # cores extraídas depois pelo slicer
            ]
            ok = run_step('DB — banco SQLite', cmd, fatal=False)
            (steps_done if ok else steps_skip).append('db')
    else:
        steps_skip.append('db')

    # ── 3. SLICE ─────────────────────────────────────────────────────────────
    if only in (None, 'slice'):
        if not check_file(args.assets_map, 'SLICE'):
            steps_skip.append('slice')
        else:
            cmd = [
                sys.executable, 'auto_slicer.py',
                '--assets', args.assets_map,
                '--out',    args.icons_dir,
                '--categories', 'body', 'eyes', 'mouth', 'hat', 'accessory', 'ears_L', 'ears_R',
            ]
            if args.preview:
                cmd.append('--preview')

            ok = run_step('SLICE — partes para OC Maker', cmd, fatal=False)
            (steps_done if ok else steps_skip).append('slice')
    else:
        steps_skip.append('slice')

    # ── 4. LORA ──────────────────────────────────────────────────────────────
    if only in (None, 'lora'):
        if not check_file(args.assets_map, 'LORA'):
            steps_skip.append('lora')
        else:
            cmd = [
                sys.executable, 'lora_prep.py',
                '--map',      args.assets_map,
                '--out',      args.lora_dir,
                '--repeats',  str(args.lora_repeats),
                '--min-size', str(args.min_sprite_size),
                '--max-game', str(args.max_per_game),
            ]
            ok = run_step('LORA — dataset de treino', cmd, fatal=False)
            (steps_done if ok else steps_skip).append('lora')
    else:
        steps_skip.append('lora')

    # ── Resumo final ─────────────────────────────────────────────────────────
    elapsed = time.time() - t_total
    banner('RESUMO')

    print(f"  Tempo total : {elapsed:.1f}s\n")
    for s in steps_done: print(f"  ✓  {s}")
    for s in steps_skip: print(f"  ○  {s} (pulado)")

    print(f"""
  Arquivos gerados:
    {args.assets_map}         ← mapa de todos os assets
    {args.db_path}            ← banco SQLite de personagens
    {args.icons_dir}/         ← partes para o OC Maker
    {args.icons_dir}/parts_index.json
    {args.lora_dir}/img/      ← dataset LoRA pronto para kohya_ss

  Próximos passos:
    1. Abrir o OC Maker: python app.py → http://localhost:5000/oc
    2. Treinar LoRA:     cd kohya_ss && python train_network.py ...
    3. Copiar LoRA para: ComfyUI/models/loras/sprunki_lora.safetensors
""")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description='Pipeline completo Sprunki',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Etapas
    p.add_argument('--only', choices=['extract','db','slice','lora'], default=None,
                   help='Rodar só uma etapa específica')

    # Caminhos
    p.add_argument('--sb3-dir',       default='sb3_files',     help='Pasta com os .sb3')
    p.add_argument('--out-organized', default='organized',      help='Saída da extração')
    p.add_argument('--assets-map',    default='assets_map.json')
    p.add_argument('--db-path',       default='sprunki.db')
    p.add_argument('--icons-dir',     default='static/icons',   help='Partes OC Maker')
    p.add_argument('--lora-dir',      default='lora_dataset',   help='Dataset LoRA')

    # Parâmetros
    p.add_argument('--workers',         type=int,   default=4)
    p.add_argument('--lora-repeats',    type=int,   default=20)
    p.add_argument('--min-sprite-size', type=int,   default=60,   help='px mínimo do sprite')
    p.add_argument('--max-per-game',    type=int,   default=30)
    p.add_argument('--preview',         action='store_true',     help='Debug do slicer')

    args = p.parse_args()
    run_pipeline(args)


if __name__ == '__main__':
    main()
