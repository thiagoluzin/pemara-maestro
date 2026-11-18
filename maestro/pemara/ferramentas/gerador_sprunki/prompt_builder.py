"""
prompt_builder.py
Motor de 6 camadas — constrói o prompt para Flux.1-dev + LoRA Sprunki.
Suporta dois modos: 'brand_analyzer' e 'oc_maker'.
"""

# ─── Trigger word da LoRA ─────────────────────────────────────────────────────
# Quando a LoRA estiver treinada, trocar para o trigger word real.
LORA_TRIGGER = "sprunki_char"

# Camada 1 sempre presente — define a anatomia base estilizada de Incredibox/Sprunki
BASE_ANATOMY = (
    f"{LORA_TRIGGER}, official Incredibox music game character sprite, "
    "slender humanoid body shape, long thin neck, slender torso, "
    "thin black legs, flat 2d color design, clean black vector outlines, "
    "solid clean flat light gray background, standing front-facing, "
    "expressive cartoon eyes, iconic music game character art style"
)

# Negative prompt fixo — usado em todos os modos
NEGATIVE_PROMPT = (
    "realistic, photograph, 3d render, pill-shaped body, egg shape, "
    "chubby fat body, short stub arms, transparent grid background, "
    "checkerboard background, text, watermark, blurry, extra limbs, "
    "deformed, nsfw, ugly, low quality, shadow, multiple characters, realistic human face"
)

# ─── Mapeamento HSL → palavra de intensidade ──────────────────────────────────
def _intensity_word(h: float, s: float, l: float) -> str:
    if s > 0.9 and l > 0.5:          return "neon"
    if s > 0.8:                       return "vivid"
    if s > 0.7 and 0.4 < l < 0.7:    return "bright"
    if s < 0.4 and l > 0.6:          return "pastel"
    if l < 0.3:                       return "dark"
    if s < 0.3:                       return "muted"
    return "vibrant"


# ─── OC MAKER ────────────────────────────────────────────────────────────────

# Mapeia opções da UI para termos de prompt
EYE_PROMPTS = {
    "normal":   "large expressive circular cartoon eyes, clean 2d vector style",
    "cute":     "large sparkling cute anime-style eyes, flat color, clean vector",
    "angry":    "sharp angry cartoon eyes, furrowed brow, minimal 2d style",
    "happy":    "happy crescent-shaped squinting eyes, simple cartoon style",
    "glowing":  "glowing flat circular neon eyes, magical aura, 2d vector",
    "tired":    "half-lidded droopy lazy eyes, simple 2d cartoon style",
    "star":     "star-shaped bright pupils, excited expression, flat vector design",
}

MOUTH_PROMPTS = {
    "smile":    "simple friendly curved cartoon smile, flat color design",
    "open":     "open mouth singing expression, flat color, clean outlines",
    "grin":     "cheeky wide grin showing teeth, minimalist vector style",
    "sad":      "downturned sad cartoon mouth, flat design",
    "neutral":  "neutral straight line mouth, minimalist style",
    "shocked":  "shocked open mouth O-shape, clean flat vector outline",
}

HAT_PROMPTS = {
    "none":         "",
    "crown":        "wearing simple flat golden crown on head, 2d vector accessory",
    "tiara":        "wearing shiny silver princess tiara, flat vector design",
    "witch":        "wearing classic pointy purple witch hat, flat 2d style",
    "cap":          "wearing backwards baseball cap, cartoon streetwear style",
    "bow":          "wearing large flat pink hair bow on head, 2d vector",
    "tophat":       "wearing elegant black top hat, flat cartoon accessory",
    "headphones":   "wearing iconic large over-ear music headphones, DJ style, flat 2d vector",
    "beanie":       "wearing cozy knit beanie hat, flat minimalist design",
    "halo":         "glowing flat yellow halo ring floating above head",
    "horns":        "small flat red demon horns on head, cartoon style",
    "antenna":      "simple grey robot antenna on head",
}

ACCESSORY_PROMPTS = {
    "none":         "",
    "wand":         "holding simple magic wand with flat star tip",
    "microphone":   "holding classic stage microphone, singer pose, flat design",
    "guitar":       "holding flat cartoon electric guitar",
    "shield":       "holding round flat color shield",
    "book":         "holding open flat style book",
    "flower":       "holding large flat vector flower",
    "sword":        "holding small flat cartoon sword",
    "staff":        "holding glowing wizard staff, flat vector design",
    "trophy":       "holding simple golden trophy, flat illustration",
}

THEME_EXTRA = {
    "princesas": "sparkles, magical aura, fairy tale aesthetic, soft glitter",
    "horror":    "eerie glow, dark shadows, spooky aesthetic, haunted",
    "cyber":     "neon circuits, holographic, futuristic, glowing edges",
    "nature":    "leaves, vines, earthy tones, natural organic feel",
    "space":     "stars, cosmic dust, nebula colors, astronaut vibes",
    "default":   "",
}


# Dicionário de descrições detalhadas dos Sprunkis de referência (Pyramixed / Sprunki)
REFERENCE_DESCRIPTIONS = {
    "ACID": "inspired by ACID character, neon lime green toxic skin, melting acid drops, wide insane button eyes, crazy wide cartoon smile",
    "Scary ACID": "inspired by Scary ACID horror character, melting dark green acid, scary bloody eyes, sharp black teeth, creepy horror game monster look",
    "Animus": "inspired by Animus character, dark shadowy black body silhouette, glowing bright red eyes, dark smoke aura, mysterious and spooky",
    "Black": "inspired by Black character, solid deep black colored skin, simple white outlines, minimalist Incredibox buddy",
    "Bluemon": "inspired by Bluemon character, fuzzy furry blue monster, small round ears, friendly blue monster look, simple 2d cartoon",
    "Brud": "inspired by Brud character, rugged brown character, construction cap or simple brown hood, calm expression",
    "Chockle": "inspired by Chockle character, milk chocolate brown skin, melting chocolate drips on head, sweet candy aesthetic",
    "Clukr": "inspired by Clukr character, wearing yellow chicken hood with orange beak, round cartoon chicken face",
    "Coka": "inspired by Coka character, red soda can theme, carbonated bubble particles, silver pop-tab hat",
    "Cooka": "inspired by Cooka character, green chef hat, cooking aesthetic, cheerful expression",
    "Cookie": "inspired by Cookie character, cookie dough brown body, embedded dark chocolate chips, sweet biscuit look",
    "Crocus": "inspired by Crocus character, purple flower petals around neck like a collar, floral nature aesthetic",
    "Deto": "inspired by Deto character, detonator or dynamite theme, red body, fuse spark on top of head, expressive cartoon face",
    "Dozer": "inspired by Dozer character, yellow construction helmet, builder theme, sleeping or lazy expression",
    "Durple": "inspired by Durple character, light purple skin, classic relaxed Incredibox face, gray music headphones around neck",
    "Elestial": "inspired by Elestial character, celestial galaxy skin, starry sky texture, glowing cosmic aura",
    "Fanta2": "inspired by Fanta2 orange soda theme, vibrant orange color, carbonated bubbles, bottle cap crown",
    "Fun Bot": "inspired by Fun Bot robot character, metallic gray chassis, glowing neon green visor screen, antennas, bolt details",
    "Garnold": "inspired by Garnold character, classic green mascot look, simple round head, wide grin, cheerful music buddy",
    "Gatoman": "inspired by Gatoman character, black cat ears hood, yellow cat pupils, sleek black cat aesthetic",
    "Glix": "inspired by Glix character, shiny cyan crystal texture, holographic light blue body, futuristic glowing edges",
    "Goldy": "inspired by Goldy character, shiny metallic gold body, wearing golden king crown, rich royal theme",
    "Gray": "inspired by Gray character, solid gray body color, minimalist classic Incredibox style, quiet expression",
    "Greenmon": "inspired by Greenmon character, fuzzy furry green monster, friendly creature aesthetic, big circular eyes",
    "Gummo": "inspired by Gummo character, pink bubblegum texture, sticky sweet bubblegum look, chewing bubble expression",
    "Horson": "inspired by Horson character, horse mascot head hood, friendly animal game character sprite",
    "Jevin": "inspired by Jevin character, blue slime body, semi-translucent gelatinous texture, dripping slime head",
    "Klato": "inspired by Klato character, three-eyed alien monster, green skin, cosmic space traveler theme",
    "Lemon John": "inspired by Lemon John character, giant yellow lemon-shaped head, yellow lemon skin, small black eyes, funny neutral expression",
    "Mayie": "inspired by Mayie character, soft pastel pink cotton candy look, fluffy hair details",
    "Medio": "inspired by Medio character, retro green game console aesthetic, pixelated visor display",
    "Mr Fun Computer": "inspired by Mr Fun Computer character, old vintage gray CRT monitor for a head, green scanlines on screen, electronic computer buddy",
    "Mr Sun": "inspired by Mr Sun character, bright yellow head with solar rays around head, happy smiling solar mascot",
    "Mr Tree": "inspired by Mr Tree character, green tree canopy head, brown wood trunk neck, nature forest aesthetic",
    "Oren": "inspired by Oren character, orange fruit head with small green leaves on top, vibrant orange skin, large eyes",
    "Oreoy": "inspired by Oreoy character, black and white sandwich cookie design, cream filling layer detail",
    "OWAKCX": "inspired by OWAKCX character, vibrant lime green skin, crazy spiky lime green hair extensions, asymmetrical eyes, friendly smile",
    "PAXO": "inspired by PAXO character, packaging box head, cardboard texture, industrial mail delivery theme",
    "Pencie": "inspired by Pencie character, pencil-shaped long body, yellow and pink graphite tip hat",
    "Peppie": "inspired by Peppie character, red chili pepper theme, green stem hat, spicy hot look",
    "Pinki": "inspired by Pinki character, cute pastel pink body, large pink hair bow, sweet friendly look",
    "Polo": "inspired by Polo character, classic white shirt Incredibox mascot, red cap",
    "Purplemon": "inspired by Purplemon character, fuzzy purple fur monster, goofy smile",
    "Raddy": "inspired by Raddy character, bold red skin, red spiky hair, relaxed sleepy eyes",
    "Redmon": "inspired by Redmon character, fuzzy red monster body, expressive look",
    "Scary Simon": "inspired by Scary Simon horror character, sinister black shadowy figure, glowing white eyes, creepy wide grin",
}


def _clean_ref_desc(char_name: str) -> str:
    desc = REFERENCE_DESCRIPTIONS.get(char_name, "")
    if not desc:
        return ""
    # Remover o prefixo comum "inspired by <Nome> character, " ou similar
    prefix_normal = f"inspired by {char_name} character, "
    prefix_horror = f"inspired by {char_name} horror character, "
    prefix_theme  = f"inspired by {char_name} orange soda theme, "
    prefix_simple = f"inspired by {char_name}, "
    
    if desc.startswith(prefix_normal):
        return desc[len(prefix_normal):]
    elif desc.startswith(prefix_horror):
        return desc[len(prefix_horror):]
    elif desc.startswith(prefix_theme):
        return desc[len(prefix_theme):]
    elif desc.startswith(prefix_simple):
        return desc[len(prefix_simple):]
    
    # Fallback genérico de remoção
    to_remove = f"inspired by {char_name}"
    if desc.startswith(to_remove):
        cleaned = desc[len(to_remove):].strip()
        if cleaned.startswith("character,"):
            cleaned = cleaned[len("character,"):].strip()
        elif cleaned.startswith("horror character,"):
            cleaned = cleaned[len("horror character,"):].strip()
        elif cleaned.startswith(","):
            cleaned = cleaned[1:].strip()
        return cleaned
    return desc


def build_oc_maker_prompt(data: dict) -> dict:
    """
    Constrói prompt para o OC Maker.

    data keys:
        body_color          str  ex: "pastel pink", "#FF69B4"
        eyes            str  chave de EYE_PROMPTS
        mouth           str  chave de MOUTH_PROMPTS
        hat             str  chave de HAT_PROMPTS
        accessory       str  chave de ACCESSORY_PROMPTS
        theme           str  chave de THEME_EXTRA
        extra_desc      str  descrição livre opcional
        reference_character str chave de REFERENCE_DESCRIPTIONS ou "none"
        body_character  str nome do personagem de referência para o corpo ou "none"
        eyes_character  str nome do personagem de referência para os olhos ou "none"
        mouth_character str nome do personagem de referência para a boca ou "none"
        hat_character   str nome do personagem de referência para o chapéu ou "none"
        accessory_character str nome do personagem de referência para o acessório ou "none"
    """
    body_color  = data.get("body_color", "pastel purple")
    eyes        = EYE_PROMPTS.get(data.get("eyes", "cute"), data.get("eyes", "cute eyes"))
    mouth       = MOUTH_PROMPTS.get(data.get("mouth", "smile"), data.get("mouth", "smiling"))
    hat         = HAT_PROMPTS.get(data.get("hat", "none"), "")
    accessory   = ACCESSORY_PROMPTS.get(data.get("accessory", "none"), "")
    theme       = THEME_EXTRA.get(data.get("theme", "default"), "")
    extra       = data.get("extra_desc", "").strip()
    ref_char    = data.get("reference_character", "none")
    
    # Partes individuais
    body_char   = data.get("body_character", "none")
    eyes_char   = data.get("eyes_character", "none")
    mouth_char  = data.get("mouth_character", "none")
    hat_char    = data.get("hat_character", "none")
    acc_char    = data.get("accessory_character", "none")
    
    is_composite = any(c != "none" for c in [body_char, eyes_char, mouth_char, hat_char, acc_char])

    # Camada 1: base
    parts = [BASE_ANATOMY]

    if is_composite:
        # Camada de composição de referências
        if body_char != "none":
            ref_desc = _clean_ref_desc(body_char)
            desc_suffix = f" ({ref_desc})" if ref_desc else ""
            parts.append(f"body structure and style of {body_char} character{desc_suffix}")
        else:
            parts.append(f"solid {body_color} colored body")
            
        if eyes_char != "none":
            ref_desc = _clean_ref_desc(eyes_char)
            desc_suffix = f" ({ref_desc})" if ref_desc else ""
            parts.append(f"eyes style and expression of {eyes_char} character{desc_suffix}")
        else:
            parts.append(eyes)
            
        if mouth_char != "none":
            ref_desc = _clean_ref_desc(mouth_char)
            desc_suffix = f" ({ref_desc})" if ref_desc else ""
            parts.append(f"mouth shape and expression of {mouth_char} character{desc_suffix}")
        else:
            parts.append(mouth)
            
        if hat_char != "none":
            ref_desc = _clean_ref_desc(hat_char)
            desc_suffix = f" ({ref_desc})" if ref_desc else ""
            parts.append(f"wearing head accessory of {hat_char} character{desc_suffix}")
        elif hat:
            parts.append(hat)
            
        if acc_char != "none":
            ref_desc = _clean_ref_desc(acc_char)
            desc_suffix = f" ({ref_desc})" if ref_desc else ""
            parts.append(f"holding item of {acc_char} character{desc_suffix}")
        elif accessory:
            parts.append(accessory)
    else:
        # Lógica antiga de compatibilidade
        ref_desc = REFERENCE_DESCRIPTIONS.get(ref_char, "")
        if ref_desc:
            parts.append(ref_desc)
        parts.append(f"solid {body_color} colored body")
        parts.append(eyes)
        parts.append(mouth)
        if hat:        parts.append(hat)
        if accessory:  parts.append(accessory)

    # Camada 4: tema
    if theme:      parts.append(theme)

    # Camada 5: extra livre
    if extra:      parts.append(extra)

    # Camada 6: fechamento técnico
    parts.append("high quality illustration, game ready sprite")

    prompt = ", ".join(p for p in parts if p)


    return {
        "prompt":          prompt,
        "negative_prompt": NEGATIVE_PROMPT,
        "source":          "oc_maker",
        "params": {
            "width":               768,
            "height":              768,
            "num_inference_steps": 25,
            "guidance_scale":      3.5,
        }
    }


# ─── BRAND ANALYZER ──────────────────────────────────────────────────────────

def build_brand_prompt(data: dict) -> dict:
    """
    Constrói prompt para o Brand Analyzer.

    data keys:
        brand_name      str
        palette         list[dict]  saída do brand_analyzer.py
        style_tags      list[str]   saída do CLIP
        has_mascot      bool
        is_food_brand   bool
        is_drink_brand  bool
        extra_desc      str         opcional
    """
    brand_name  = data.get("brand_name", "custom brand")
    palette     = data.get("palette", [])
    style_tags  = data.get("style_tags", [])[:4]
    has_mascot  = data.get("has_mascot", False)
    is_food     = data.get("is_food_brand", False)
    is_drink    = data.get("is_drink_brand", False)
    extra       = data.get("extra_desc", "").strip()

    # Camada 1: base
    parts = [BASE_ANATOMY]

    # Camada 2: identidade da marca
    parts.append(f"inspired by {brand_name} brand")

    # Camada 3: paleta de cores
    if palette:
        colors = [c["name"] for c in palette[:3]]
        hexes  = [c["hex"]  for c in palette[:3]]
        h, s, l = palette[0]["hsl"]
        intensity = _intensity_word(h, s, l)
        parts.append(f"{intensity} {', '.join(colors)} color scheme")
        parts.append(f"body color {hexes[0]}")
        if len(hexes) > 1:
            parts.append(f"accent color {hexes[1]}")

    # Camada 4: estilo CLIP
    if style_tags:
        parts.append(f"{', '.join(style_tags)} aesthetic")

    # Camada 5: condicionais de marca
    if has_mascot:
        parts.append(f"character inspired by {brand_name} mascot")
    if is_food or is_drink:
        parts.append(f"wearing {brand_name} themed accessories")

    # Extra livre
    if extra:
        parts.append(extra)

    # Camada 6: fechamento técnico
    parts.append("high quality illustration, game ready sprite")

    prompt = ", ".join(p for p in parts if p)

    return {
        "prompt":          prompt,
        "negative_prompt": NEGATIVE_PROMPT,
        "source":          "brand_analyzer",
        "params": {
            "width":               1024,
            "height":              1024,
            "num_inference_steps": 28,
            "guidance_scale":      3.5,
        }
    }


# ─── Entry point unificado ────────────────────────────────────────────────────

def build_final_prompt(source_type: str, data: dict) -> dict:
    """
    Entry point único — roteado por source_type.
    Retorna dict com: prompt, negative_prompt, source, params.
    """
    if source_type == "oc_maker":
        return build_oc_maker_prompt(data)
    elif source_type == "brand_analyzer":
        return build_brand_prompt(data)
    else:
        raise ValueError(f"source_type inválido: {source_type!r}")
