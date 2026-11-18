"""
sprunki_db_builder.py
Constrói o banco de dados SQLite com todos os personagens Sprunki existentes.

Dependências:
    pip install Pillow colorthief numpy

Uso:
    python sprunki_db_builder.py --assets assets_map.json --db sprunki.db
"""

import json
import sqlite3
import argparse
import os
import sys
from pathlib import Path

# ─── Dependências opcionais (extração de cor) ────────────────────────────────
try:
    from colorthief import ColorThief
    from PIL import Image
    import numpy as np
    HAS_COLOR_TOOLS = True
except ImportError:
    HAS_COLOR_TOOLS = False
    print("[AVISO] colorthief / Pillow não encontrados. Cores serão NULL no DB.")
    print("        pip install Pillow colorthief numpy")


# ─── Filtros ──────────────────────────────────────────────────────────────────

# Palavras-chave que identificam sprites de UI (não são personagens)
UI_KEYWORDS = {
    "button", "buttons", "bar", "bars", "settings", "reset", "close",
    "more", "preview", "stage", "gallery", "polo", "dark mode",
    "accent color", "icons", "sprite2", "sprite10", "sprite1",
    "leftarrow", "leftarrow2", "background", "backdrop",
    "achievement", "credit", "galleryimages", "old gallery",
}

# Palavras-chave que indicam personagem real de jogo
CHARACTER_KEYWORDS = {
    "beat", "melody", "voice", "effect", "acid", "tox", "sulfur",
    "broker", "moch", "coka", "peppi", "thysto", "animus", "penz",
    "skymon", "paxo", "medio", "glix", "beautiful sun",
}

# Tipos de personagem por prefixo de nome
TYPE_MAP = {
    "beat":    "Beat",
    "melody":  "Melody",
    "voice":   "Voice",
    "effect":  "Effect",
    "acid":    "Special",
    "tox":     "Special",
    "sulfur":  "Special",
    "broker":  "Special",
    "moch":    "Special",
    "coka":    "Special",
    "peppi":   "Special",
    "thysto":  "Special",
    "animus":  "Special",
    "penz":    "Special",
    "skymon":  "Special",
    "paxo":    "Special",
    "medio":   "Special",
    "glix":    "Special",
}


def is_character(name: str) -> bool:
    """Retorna True se o sprite for um personagem jogável."""
    n = name.lower().strip()
    for kw in UI_KEYWORDS:
        if kw in n:
            return False
    # sons genéricos de UI
    return True


def get_character_type(name: str) -> str:
    """Classifica o personagem por tipo."""
    n = name.lower().strip()
    for prefix, ctype in TYPE_MAP.items():
        if n.startswith(prefix):
            return ctype
    # Verifica keywords de personagem
    for kw in CHARACTER_KEYWORDS:
        if kw in n:
            return "Special"
    return "Unknown"


def is_ui_sound(sound_path: str | None) -> bool:
    """Sons genéricos de UI não qualificam o personagem."""
    if sound_path is None:
        return True
    filename = Path(sound_path).name.lower()
    return filename in {"pop.wav", "click.wav", "wrong.wav"}


# ─── Extração de cores ────────────────────────────────────────────────────────

def extract_palette(image_path: str, n_colors: int = 5) -> list[str] | None:
    """
    Extrai a paleta de cores dominantes de um sprite PNG.
    Ignora pixels transparentes (alpha < 128).
    Retorna lista de hex strings ex: ['#FF3300', '#00AAFF', ...]
    """
    if not HAS_COLOR_TOOLS:
        return None

    path = Path(image_path)
    if not path.exists():
        return None

    try:
        img = Image.open(path).convert("RGBA")
        arr = np.array(img)

        # Filtra pixels transparentes
        mask = arr[:, :, 3] >= 128
        visible = arr[mask][:, :3]  # apenas RGB dos pixels opacos

        if len(visible) == 0:
            return None

        # K-means simples com sklearn (se disponível) ou fallback
        try:
            from sklearn.cluster import KMeans
            km = KMeans(n_clusters=n_colors, n_init=10, random_state=42)
            km.fit(visible)
            centers = km.cluster_centers_.astype(int)
            palette = [f"#{r:02X}{g:02X}{b:02X}" for r, g, b in centers]
        except ImportError:
            # Fallback: usa colorthief diretamente no arquivo
            ct = ColorThief(image_path)
            raw = ct.get_palette(color_count=n_colors, quality=5)
            palette = [f"#{r:02X}{g:02X}{b:02X}" for r, g, b in raw]

        return palette

    except Exception as e:
        print(f"  [ERRO cor] {image_path}: {e}")
        return None


def rgb_to_hsl(hex_color: str) -> tuple[float, float, float]:
    """Converte hex → HSL para análise de tom."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    cmax, cmin = max(r, g, b), min(r, g, b)
    delta = cmax - cmin
    l = (cmax + cmin) / 2
    s = 0 if delta == 0 else delta / (1 - abs(2 * l - 1))
    if delta == 0:
        h = 0.0
    elif cmax == r:
        h = 60 * (((g - b) / delta) % 6)
    elif cmax == g:
        h = 60 * ((b - r) / delta + 2)
    else:
        h = 60 * ((r - g) / delta + 4)
    return round(h, 1), round(s, 3), round(l, 3)


# ─── Banco de dados ───────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS characters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id         INTEGER NOT NULL REFERENCES games(id),
    name            TEXT NOT NULL,
    char_type       TEXT,           -- Beat / Melody / Voice / Effect / Special / Unknown
    image_path      TEXT,
    sound_path      TEXT,
    palette_json    TEXT,           -- JSON array de hex strings
    dominant_color  TEXT,           -- hex da cor mais dominante
    hue             REAL,           -- 0-360
    saturation      REAL,           -- 0-1
    lightness       REAL,           -- 0-1
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS brand_analyses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_name      TEXT NOT NULL,
    image_path      TEXT,
    palette_json    TEXT,
    style_tags_json TEXT,
    prompt_used     TEXT,
    generated_char  INTEGER REFERENCES characters(id),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_char_game    ON characters(game_id);
CREATE INDEX IF NOT EXISTS idx_char_type    ON characters(char_type);
CREATE INDEX IF NOT EXISTS idx_char_hue     ON characters(hue);
"""


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def insert_game(conn: sqlite3.Connection, name: str) -> int:
    cur = conn.execute(
        "INSERT OR IGNORE INTO games (name) VALUES (?)", (name,)
    )
    if cur.lastrowid:
        return cur.lastrowid
    return conn.execute("SELECT id FROM games WHERE name=?", (name,)).fetchone()[0]


def insert_character(conn: sqlite3.Connection, game_id: int, char: dict) -> None:
    conn.execute("""
        INSERT OR IGNORE INTO characters
            (game_id, name, char_type, image_path, sound_path,
             palette_json, dominant_color, hue, saturation, lightness)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        game_id,
        char["name"],
        char["char_type"],
        char["image"],
        char["sound"],
        json.dumps(char["palette"]) if char["palette"] else None,
        char["palette"][0] if char["palette"] else None,
        char["hue"],
        char["saturation"],
        char["lightness"],
    ))


# ─── Pipeline principal ───────────────────────────────────────────────────────

def build_database(assets_path: str, db_path: str, extract_colors: bool = True) -> None:
    print(f"\n{'='*60}")
    print(f"  Sprunki DB Builder")
    print(f"  Assets : {assets_path}")
    print(f"  Saída  : {db_path}")
    print(f"{'='*60}\n")

    with open(assets_path, "r", encoding="utf-8") as f:
        assets = json.load(f)

    conn = init_db(db_path)

    total_games = 0
    total_chars = 0
    skipped_ui = 0

    for game_name, game_data in assets.items():
        game_id = insert_game(conn, game_name)
        total_games += 1
        game_chars = 0

        characters = game_data.get("characters", [])
        for sprite in characters:
            name = sprite.get("name", "").strip()
            image = sprite.get("image")
            sound = sprite.get("sound")

            # Filtra UI
            if not is_character(name):
                skipped_ui += 1
                continue

            # Sons de UI não qualificam (mas não descartamos o personagem,
            # apenas marcamos que não tem áudio próprio)
            has_real_sound = not is_ui_sound(sound)
            if not has_real_sound:
                sound = None  # normaliza

            char_type = get_character_type(name)

            # Extração de cor
            palette = None
            hue = saturation = lightness = None
            if extract_colors and HAS_COLOR_TOOLS and image:
                palette = extract_palette(image)
                if palette:
                    hue, saturation, lightness = rgb_to_hsl(palette[0])

            char_data = {
                "name":        name,
                "char_type":   char_type,
                "image":       image,
                "sound":       sound,
                "palette":     palette,
                "hue":         hue,
                "saturation":  saturation,
                "lightness":   lightness,
            }

            insert_character(conn, game_id, char_data)
            game_chars += 1
            total_chars += 1

        conn.commit()
        print(f"  [{game_name[:50]}]  {game_chars} personagens inseridos")

    conn.close()

    print(f"\n{'─'*60}")
    print(f"  Jogos processados : {total_games}")
    print(f"  Personagens no DB : {total_chars}")
    print(f"  Sprites UI pulados: {skipped_ui}")
    print(f"  DB salvo em       : {db_path}")
    print(f"{'─'*60}\n")


def export_summary_json(db_path: str, out_path: str) -> None:
    """Exporta um JSON resumido do DB para inspeção rápida."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    games = conn.execute("SELECT * FROM games").fetchall()
    summary = {}
    for g in games:
        chars = conn.execute(
            "SELECT name, char_type, dominant_color, image_path, sound_path "
            "FROM characters WHERE game_id=?", (g["id"],)
        ).fetchall()
        summary[g["name"]] = [dict(c) for c in chars]

    conn.close()

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"  Resumo exportado: {out_path}")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Constrói o banco de dados de Sprunkis")
    parser.add_argument("--assets", default="assets_map.json", help="Caminho do assets_map.json")
    parser.add_argument("--db",     default="sprunki.db",      help="Caminho do banco SQLite de saída")
    parser.add_argument("--no-colors", action="store_true",    help="Pular extração de cores (rápido)")
    parser.add_argument("--export-json", default="sprunki_summary.json", help="Exportar resumo em JSON")
    args = parser.parse_args()

    if not os.path.exists(args.assets):
        print(f"[ERRO] Arquivo não encontrado: {args.assets}")
        sys.exit(1)

    build_database(
        assets_path=args.assets,
        db_path=args.db,
        extract_colors=not args.no_colors,
    )

    export_summary_json(args.db, args.export_json)


if __name__ == "__main__":
    main()
