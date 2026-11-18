from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_THEME_COLOR
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_CONNECTOR
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


OUT = Path(r"E:\Pemara\deliveries\Maestro_Workflow_MiniMax_H3_Completo_20260816.pptx")

W = Inches(13.333333)
H = Inches(7.5)

NAVY = RGBColor(9, 18, 35)
NAVY_2 = RGBColor(15, 30, 54)
PANEL = RGBColor(22, 39, 66)
PANEL_2 = RGBColor(29, 50, 82)
WHITE = RGBColor(246, 249, 252)
MUTED = RGBColor(169, 185, 204)
CYAN = RGBColor(41, 210, 222)
BLUE = RGBColor(57, 126, 255)
PURPLE = RGBColor(151, 104, 255)
YELLOW = RGBColor(255, 197, 61)
GREEN = RGBColor(62, 211, 145)
RED = RGBColor(255, 94, 111)
ORANGE = RGBColor(255, 139, 60)
BLACK = RGBColor(6, 10, 18)


def add_textbox(slide, x, y, w, h, text="", *, size=20, color=WHITE,
                bold=False, font="Aptos", align=PP_ALIGN.LEFT,
                valign=MSO_ANCHOR.TOP, margin=0.08, line_spacing=1.0):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Inches(margin)
    tf.margin_right = Inches(margin)
    tf.margin_top = Inches(margin)
    tf.margin_bottom = Inches(margin)
    tf.vertical_anchor = valign
    p = tf.paragraphs[0]
    p.text = text
    for paragraph in tf.paragraphs:
        paragraph.alignment = align
        paragraph.line_spacing = line_spacing
        for run in paragraph.runs:
            run.font.name = font
            run.font.size = Pt(size)
            run.font.bold = bold
            run.font.color.rgb = color
    return box


def add_rich_text(slide, x, y, w, h, runs, *, size=20, valign=MSO_ANCHOR.TOP,
                  align=PP_ALIGN.LEFT, margin=0.08):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.clear()
    tf.margin_left = Inches(margin)
    tf.margin_right = Inches(margin)
    tf.margin_top = Inches(margin)
    tf.margin_bottom = Inches(margin)
    tf.vertical_anchor = valign
    p = tf.paragraphs[0]
    p.alignment = align
    for text, color, bold in runs:
        r = p.add_run()
        r.text = text
        r.font.name = "Aptos"
        r.font.size = Pt(size)
        r.font.color.rgb = color
        r.font.bold = bold
    return box


def add_round_rect(slide, x, y, w, h, fill=PANEL, line=None, radius=True,
                   transparency=0):
    shape_type = MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE if radius else MSO_AUTO_SHAPE_TYPE.RECTANGLE
    shp = slide.shapes.add_shape(shape_type, x, y, w, h)
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if transparency:
        shp.fill.transparency = transparency
    shp.line.color.rgb = line or fill
    return shp


def set_shape_text(shape, text, *, size=16, color=WHITE, bold=False,
                   align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE, font="Aptos"):
    tf = shape.text_frame
    tf.clear()
    tf.margin_left = Inches(0.08)
    tf.margin_right = Inches(0.08)
    tf.margin_top = Inches(0.04)
    tf.margin_bottom = Inches(0.04)
    tf.vertical_anchor = valign
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = align
    r = p.runs[0]
    r.font.name = font
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    return shape


def add_pill(slide, x, y, w, text, color=CYAN, *, text_color=NAVY, size=11):
    p = add_round_rect(slide, x, y, w, Inches(0.32), fill=color, line=color)
    set_shape_text(p, text.upper(), size=size, color=text_color, bold=True)
    return p


def add_bullets(slide, x, y, w, h, items: Sequence[str], *, size=17,
                color=WHITE, bullet_color=CYAN, gap=8, levels=None):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Inches(0.05)
    tf.margin_right = Inches(0.05)
    tf.margin_top = 0
    tf.margin_bottom = 0
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        level = levels[i] if levels else 0
        p.level = level
        p.space_after = Pt(gap)
        p.text = item
        p.font.name = "Aptos"
        p.font.size = Pt(size - level * 2)
        p.font.color.rgb = color
        p.line_spacing = 1.05
        p._p.get_or_add_pPr().insert(0, p._p._new_buChar()) if False else None
        # python-pptx does not expose bullet color independently; prefix creates a reliable visual bullet.
        p.text = ("• " if level == 0 else "– ") + item
    return box


def add_card(slide, x, y, w, h, title, body=None, *, accent=CYAN,
             number=None, title_size=17, body_size=13):
    add_round_rect(slide, x, y, w, h, fill=PANEL, line=PANEL_2)
    slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, x, y, Inches(0.06), h).fill.solid()
    stripe = slide.shapes[-1]
    stripe.fill.fore_color.rgb = accent
    stripe.line.color.rgb = accent
    tx = x + Inches(0.22)
    if number is not None:
        circ = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.OVAL, tx, y + Inches(0.16), Inches(0.38), Inches(0.38))
        circ.fill.solid(); circ.fill.fore_color.rgb = accent; circ.line.color.rgb = accent
        set_shape_text(circ, str(number), size=12, color=NAVY, bold=True)
        tx += Inches(0.52)
    add_textbox(slide, tx, y + Inches(0.12), w - (tx - x) - Inches(0.12), Inches(0.42),
                title, size=title_size, color=WHITE, bold=True, valign=MSO_ANCHOR.MIDDLE)
    if body:
        add_textbox(slide, x + Inches(0.22), y + Inches(0.62), w - Inches(0.36), h - Inches(0.74),
                    body, size=body_size, color=MUTED, line_spacing=1.0)


def add_code(slide, x, y, w, h, text, *, size=13, accent=CYAN):
    add_round_rect(slide, x, y, w, h, fill=BLACK, line=PANEL_2)
    slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, x, y, Inches(0.05), h).fill.solid()
    bar = slide.shapes[-1]; bar.fill.fore_color.rgb = accent; bar.line.color.rgb = accent
    return add_textbox(slide, x + Inches(0.16), y + Inches(0.08), w - Inches(0.25), h - Inches(0.16),
                       text, size=size, color=RGBColor(216, 230, 239), font="Cascadia Mono",
                       valign=MSO_ANCHOR.MIDDLE)


def add_arrow(slide, x1, y1, x2, y2, color=CYAN, width=2.2):
    line = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, x1, y1, x2, y2)
    line.line.color.rgb = color
    line.line.width = Pt(width)
    # Add a small terminal triangle because arrowhead support varies by Office version.
    tri = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ISOSCELES_TRIANGLE,
                                 x2 - Inches(0.07), y2 - Inches(0.07), Inches(0.14), Inches(0.14))
    tri.rotation = 90 if x2 >= x1 else 270
    tri.fill.solid(); tri.fill.fore_color.rgb = color; tri.line.color.rgb = color
    return line


def base_slide(prs, title, section, number, subtitle=None):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background.fill
    bg.solid(); bg.fore_color.rgb = NAVY
    # top accent
    band = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.RECTANGLE, 0, 0, W, Inches(0.08))
    band.fill.solid(); band.fill.fore_color.rgb = CYAN; band.line.color.rgb = CYAN
    add_pill(slide, Inches(0.56), Inches(0.32), Inches(1.65), section, CYAN)
    add_textbox(slide, Inches(0.56), Inches(0.78), Inches(11.9), Inches(0.58),
                title, size=29, color=WHITE, bold=True, valign=MSO_ANCHOR.MIDDLE)
    if subtitle:
        add_textbox(slide, Inches(0.58), Inches(1.34), Inches(11.8), Inches(0.42),
                    subtitle, size=13, color=MUTED)
    # footer
    add_textbox(slide, Inches(0.56), Inches(7.10), Inches(8.5), Inches(0.2),
                "Maestro MiniMax H3 • workflow de produção e reconstrução", size=9, color=MUTED)
    add_textbox(slide, Inches(12.1), Inches(7.06), Inches(0.6), Inches(0.24),
                f"{number:02d}", size=10, color=CYAN, bold=True, align=PP_ALIGN.RIGHT)
    return slide


def add_notes(slide, text: str):
    tf = slide.notes_slide.notes_text_frame
    tf.text = text.strip()


def add_phase_rail(slide, active: int):
    labels = ["Roteiro", "Âncoras", "Prompt", "H3", "Aprovação", "Acabamento", "Áudio"]
    x0, y, total = Inches(0.62), Inches(6.63), Inches(12.05)
    step = total / len(labels)
    for i, label in enumerate(labels):
        color = CYAN if i == active else PANEL_2
        shp = add_round_rect(slide, x0 + step * i, y, step - Inches(0.05), Inches(0.30), fill=color, line=color)
        set_shape_text(shp, label, size=9, color=NAVY if i == active else MUTED, bold=i == active)


def add_title_slide(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background.fill; bg.solid(); bg.fore_color.rgb = NAVY
    # layered cinematic bars
    for x, y, w, h, color, trans in [
        (Inches(7.8), Inches(-0.5), Inches(6.2), Inches(8.5), BLUE, 48),
        (Inches(9.2), Inches(-0.4), Inches(4.7), Inches(8.2), PURPLE, 28),
        (Inches(10.7), Inches(-0.4), Inches(3.3), Inches(8.2), CYAN, 8),
    ]:
        s = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.PARALLELOGRAM, x, y, w, h)
        s.fill.solid(); s.fill.fore_color.rgb = color; s.fill.transparency = trans
        s.line.color.rgb = color; s.line.transparency = 100
    add_pill(slide, Inches(0.7), Inches(0.70), Inches(2.12), "GUIA OPERACIONAL", YELLOW, text_color=NAVY)
    add_textbox(slide, Inches(0.72), Inches(1.45), Inches(7.6), Inches(1.55),
                "Workflow completo\ndo Maestro MiniMax H3", size=38, color=WHITE, bold=True,
                valign=MSO_ANCHOR.MIDDLE)
    add_textbox(slide, Inches(0.76), Inches(3.25), Inches(6.9), Inches(1.20),
                "Como planejar, gerar, aprovar, finalizar e reconstruir o sistema em outro PC — sem crossfade, congelamento ou perda silenciosa de qualidade.",
                size=19, color=MUTED, line_spacing=1.1)
    # system chain
    labels = [("Qwen", BLUE), ("H3", CYAN), ("RIFE", PURPLE), ("Foley", YELLOW)]
    x = Inches(0.76)
    for i, (lab, col) in enumerate(labels):
        c = add_round_rect(slide, x + Inches(1.48) * i, Inches(5.25), Inches(1.26), Inches(0.62), fill=PANEL, line=col)
        set_shape_text(c, lab, size=15, color=col, bold=True)
        if i < len(labels) - 1:
            add_arrow(slide, x + Inches(1.48) * i + Inches(1.27), Inches(5.56),
                      x + Inches(1.48) * (i + 1) - Inches(0.04), Inches(5.56), color=MUTED, width=1.4)
    add_textbox(slide, Inches(0.76), Inches(6.63), Inches(5.0), Inches(0.28),
                "Contrato: maestro-minimax-h3-production@2026-08-16", size=10, color=MUTED)
    add_textbox(slide, Inches(11.95), Inches(6.94), Inches(0.65), Inches(0.25),
                "01", size=10, color=NAVY, bold=True, align=PP_ALIGN.RIGHT)
    add_notes(slide, """
Objetivo desta apresentação: permitir que qualquer operador autorizado compreenda o workflow e execute a produção de ponta a ponta. A apresentação separa claramente geração, aprovação humana, acabamento e reconstrução do sistema. O único motor de vídeo de produção é o MiniMax H3; os demais modelos cumprem papéis auxiliares e nunca aprovam saídas.
""")


def build_deck():
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H
    prs.core_properties.title = "Workflow completo do Maestro MiniMax H3"
    prs.core_properties.subject = "Produção de clipes, arquitetura de modelos e restauração em outro PC"
    prs.core_properties.author = "Pemara"
    prs.core_properties.keywords = "Maestro, MiniMax H3, Qwen, RIFE, Foley, workflow, vídeo"
    add_title_slide(prs)

    # 02
    s = base_slide(prs, "O resultado que este workflow entrega", "VISÃO GERAL", 2,
                   "Um processo repetível, auditável e aprovado por etapa")
    cards = [
        ("Direção controlada", "Roteiro e continuidade viram contratos verificáveis por take.", CYAN),
        ("Identidade preservada", "Fotos âncora aprovadas impedem deriva de personagem e cenário.", BLUE),
        ("Movimento contínuo", "Conectores FL2VA sem crossfade, freeze, hold ou reinício de ação.", PURPLE),
        ("Entrega profissional", "FHD/60 FPS, Foley sincronizado, loudness, hashes e rollback.", YELLOW),
    ]
    for i, (t, b, c) in enumerate(cards):
        x = Inches(0.62 + (i % 2) * 6.15); y = Inches(1.92 + (i // 2) * 2.05)
        add_card(s, x, y, Inches(5.82), Inches(1.72), t, b, accent=c, number=i+1)
    add_round_rect(s, Inches(0.62), Inches(6.12), Inches(12.05), Inches(0.55), fill=RGBColor(41, 59, 86), line=CYAN)
    add_rich_text(s, Inches(0.84), Inches(6.19), Inches(11.6), Inches(0.32), [
        ("Regra de ouro: ", YELLOW, True),
        ("nenhuma saída de modelo é aprovada automaticamente; o proprietário decide cada gate.", WHITE, False),
    ], size=14, valign=MSO_ANCHOR.MIDDLE)
    add_notes(s, """
Apresente o workflow como uma linha de produção com gates. A qualidade não vem apenas do modelo: vem da combinação entre roteiro, âncoras, prompt estruturado, preflight, geração, revisão e acabamento. A aprovação humana é obrigatória para roteiro, âncoras, takes, picture lock e áudio.
""")

    # 03
    s = base_slide(prs, "Arquitetura: um gerador, especialistas ao redor", "ARQUITETURA", 3,
                   "Cada modelo tem função limitada; somente o proprietário aprova")
    groups = [
        ("DIREÇÃO", ["project-planner", "creative-director", "diretores de take e movimento"], BLUE),
        ("ÂNCORAS", ["Qwen Image 2512", "Qwen Image Edit 2511", "QC visual humano"], PURPLE),
        ("GERAÇÃO", ["h3-prompt-writing", "Qwen3-VL-32B", "MiniMax H3 + VAEs"], CYAN),
        ("ACABAMENTO", ["RIFE 4.6", "RealESRGAN x2plus", "FFmpeg NVENC + Foley XXL"], YELLOW),
    ]
    for i, (t, items, c) in enumerate(groups):
        x = Inches(0.55 + i * 3.15)
        add_card(s, x, Inches(1.85), Inches(2.83), Inches(3.45), t, "\n".join(f"• {v}" for v in items), accent=c)
        if i < 3:
            add_arrow(s, x + Inches(2.86), Inches(3.55), x + Inches(3.10), Inches(3.55), color=MUTED, width=1.5)
    owner = add_round_rect(s, Inches(3.62), Inches(5.63), Inches(6.05), Inches(0.72), fill=RGBColor(45, 52, 67), line=GREEN)
    set_shape_text(owner, "PROPRIETÁRIO = único componente com poder de aprovação", size=17, color=GREEN, bold=True)
    add_notes(s, """
O desenho evita a ideia de que todos os modelos geram vídeo. Qwen prepara ou corrige imagens âncora; a skill oficial estrutura o prompt; Qwen3-VL codifica o contexto; MiniMax H3 gera o take; RIFE e RealESRGAN só tratam material aprovado; Foley entra depois do picture lock. Agentes ajudam a planejar e validar, mas não aprovam.
""")

    # 04
    s = base_slide(prs, "Mapa ponta a ponta: sete gates até o master", "FLUXO", 4)
    phases = [
        ("1", "Roteiro", "ação e continuidade", BLUE),
        ("2", "Âncoras", "start/end aprovadas", PURPLE),
        ("3", "Prompt", "skill oficial H3", CYAN),
        ("4", "Geração", "take nativo 24 FPS", CYAN),
        ("5", "Aprovação", "QC + proprietário", GREEN),
        ("6", "Acabamento", "FHD + 60 FPS", YELLOW),
        ("7", "Áudio", "Foley + master", ORANGE),
    ]
    x0, y = Inches(0.55), Inches(2.15)
    for i, (n, title, sub, c) in enumerate(phases):
        x = x0 + Inches(1.78) * i
        box = add_round_rect(s, x, y, Inches(1.5), Inches(1.78), fill=PANEL, line=c)
        num = s.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.OVAL, x + Inches(0.53), y - Inches(0.30), Inches(0.44), Inches(0.44))
        num.fill.solid(); num.fill.fore_color.rgb = c; num.line.color.rgb = c
        set_shape_text(num, n, size=12, color=NAVY, bold=True)
        add_textbox(s, x + Inches(0.08), y + Inches(0.38), Inches(1.34), Inches(0.42), title, size=14, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
        add_textbox(s, x + Inches(0.09), y + Inches(0.87), Inches(1.32), Inches(0.58), sub, size=11, color=MUTED, align=PP_ALIGN.CENTER)
        if i < len(phases)-1:
            add_arrow(s, x + Inches(1.53), y + Inches(0.90), x + Inches(1.74), y + Inches(0.90), color=MUTED, width=1.3)
    add_round_rect(s, Inches(1.42), Inches(4.68), Inches(10.48), Inches(1.02), fill=BLACK, line=PANEL_2)
    add_textbox(s, Inches(1.68), Inches(4.88), Inches(9.95), Inches(0.56),
                "Se um gate reprovar, volta-se à causa: roteiro, âncora, prompt, movimento ou áudio — nunca se mascara o erro na edição.",
                size=17, color=YELLOW, bold=True, align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE)
    add_notes(s, """
Explique o retorno controlado. Reprovação de identidade ou anatomia volta para a âncora; reprovação de movimento volta para prompt/contrato; reprovação de conector volta para FL2VA; reprovação de áudio volta para Foley. O editor não deve usar transição congelada para esconder falhas de geração.
""")

    # 05
    s = base_slide(prs, "Fase 1 — transformar a ideia em roteiro executável", "PRODUÇÃO", 5)
    add_card(s, Inches(0.62), Inches(1.83), Inches(3.78), Inches(3.95), "ENTRADA",
             "• objetivo do clipe\n• duração total\n• personagens e cenário\n• começo, virada e final\n• referências permitidas", accent=BLUE)
    add_card(s, Inches(4.78), Inches(1.83), Inches(3.78), Inches(3.95), "PARA CADA TAKE",
             "• duração e estado inicial\n• uma ação principal\n• posição final útil\n• câmera e efeitos\n• continuidade com o próximo", accent=CYAN)
    add_card(s, Inches(8.94), Inches(1.83), Inches(3.78), Inches(3.95), "SAÍDA APROVÁVEL",
             "• lista numerada de takes\n• mapa start/end\n• tabela de conectores\n• restrições visuais\n• gate do proprietário", accent=GREEN)
    add_phase_rail(s, 0)
    add_notes(s, """
Procedimento: escreva primeiro o arco do clipe; depois divida a duração em takes com função narrativa. Cada take deve começar no estado deixado pelo anterior e terminar em uma pose ou movimento que permita o próximo. Registre anatomia proibida, elementos obrigatórios e regras de cenário. O proprietário aprova o roteiro antes de gerar imagens.
""")

    # 06
    s = base_slide(prs, "Fase 2 — fotos âncora perfeitas antes da GPU", "PRODUÇÃO", 6,
                   "A âncora ruim vira vídeo caro e errado")
    add_card(s, Inches(0.62), Inches(1.83), Inches(4.0), Inches(4.25), "CHECKLIST DE IDENTIDADE",
             "• rosto, corpo e proporções\n• cabelo, crista, orelhas e acessórios\n• sem membros ou caudas extras\n• material e cor da roupa\n• iluminação compatível\n• live action quando exigido", accent=PURPLE)
    add_card(s, Inches(4.82), Inches(1.83), Inches(4.0), Inches(4.25), "START + END",
             "• início reproduz o take anterior\n• final já aponta a próxima ação\n• enquadramento e eixo coerentes\n• cenário e direção de luz estáveis\n• sidecar registra identidade e negativos", accent=CYAN)
    add_card(s, Inches(9.02), Inches(1.83), Inches(3.68), Inches(4.25), "REPROVAR SE...",
             "• anatomia inventada\n• estética animada indevida\n• personagem bombado/diferente\n• posição impossível\n• câmera contraditória\n• fundo mudou sem causa", accent=RED)
    add_phase_rail(s, 1)
    add_notes(s, """
Gere ou corrija as âncoras com Qwen Image/Qwen Image Edit. Antes de aprovar, amplie a imagem e confira pixels críticos: anatomia, acessórios, silhueta, textura da pele, figurino e cenário. Para FL2VA, a primeira imagem define 0,00 s e a segunda define o fim real do take. Se a âncora estiver errada, não tente consertar apenas no prompt de vídeo.
""")

    # 07
    s = base_slide(prs, "Escolher o modo H3 pelo tipo de referência", "PROMPT H3", 7)
    modes = [
        ("T2VA", "texto", "sem imagem fixa", BLUE),
        ("I2VA", "1 imagem", "âncora inicial", PURPLE),
        ("L2VA", "1 imagem", "âncora final", ORANGE),
        ("FL2VA", "2 imagens", "start + end", CYAN),
        ("Ref2VA", "múltiplas refs", "runtime ainda não ativo", RED),
    ]
    for i, (m, inp, desc, c) in enumerate(modes):
        x = Inches(0.60 + i * 2.52)
        add_card(s, x, Inches(2.03), Inches(2.28), Inches(2.92), m,
                 f"Entrada: {inp}\n\n{desc}", accent=c, title_size=20, body_size=13)
    add_round_rect(s, Inches(1.28), Inches(5.35), Inches(10.75), Inches(0.72), fill=PANEL, line=CYAN)
    add_textbox(s, Inches(1.55), Inches(5.50), Inches(10.2), Inches(0.35),
                "Para conectores e continuidade precisa, o padrão é FL2VA com duas âncoras aprovadas.",
                size=17, color=CYAN, bold=True, align=PP_ALIGN.CENTER)
    add_phase_rail(s, 2)
    add_notes(s, """
O Maestro infere o modo pelas referências entregues. T2VA serve quando não há âncora visual; I2VA fixa o início; L2VA fixa o fim; FL2VA fixa ambos e é o modo preferido para continuidade. Ref2VA possui estrutura de prompt pronta, mas runtime e pesos não estão liberados para produção.
""")

    # 08
    s = base_slide(prs, "Fase 3 — o prompt oficial é uma timeline, não um parágrafo", "PROMPT H3", 8)
    blocks = [
        ("Identidade", "quem aparece e o que não pode mudar", BLUE),
        ("Keyframes", "estado inicial e final alinhados às âncoras", PURPLE),
        ("Timeline", "beats com tempo, ação, câmera e física", CYAN),
        ("Descrição integrada", "visual, movimento, ambiente e continuidade", GREEN),
        ("Som", "soundscape e música não diegética", YELLOW),
    ]
    for i, (t, b, c) in enumerate(blocks):
        y = Inches(1.78 + i * 0.93)
        add_card(s, Inches(0.62), y, Inches(5.25), Inches(0.75), t, None, accent=c, number=i+1, title_size=15)
        add_textbox(s, Inches(6.08), y + Inches(0.04), Inches(3.18), Inches(0.60), b,
                    size=14, color=MUTED, valign=MSO_ANCHOR.MIDDLE)
    add_round_rect(s, Inches(9.45), Inches(1.82), Inches(2.85), Inches(1.45), fill=BLACK, line=CYAN)
    add_textbox(s, Inches(9.67), Inches(2.08), Inches(2.4), Inches(0.75),
                "Compilação local\nsem API externa", size=18, color=CYAN, bold=True,
                align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE)
    add_phase_rail(s, 2)
    add_notes(s, """
Use a skill oficial h3-prompt-writing pinada localmente. Ela preserva a direção criativa e acrescenta a estrutura que o H3 espera. O compilador inclui alinhamento temporal, integrated_multimodal_description, overall_soundscape e non_diegetic_music. Um prompt já compilado é reconhecido e não recebe seções duplicadas.
""")

    # 09
    s = base_slide(prs, "Exemplo de timeline para um take FL2VA", "PROMPT H3", 9,
                   "Um movimento útil em todo o take, sem teleporte narrativo")
    timeline = [
        ("0,00–1,20 s", "Partida", "pose da âncora inicial; peso corporal já em movimento", BLUE),
        ("1,20–4,80 s", "Ação", "aceleração, impacto e reação com física legível", CYAN),
        ("4,80–7,20 s", "Continuidade", "ação irreversível leva ao enquadramento final", PURPLE),
        ("7,20–8,00 s", "Chegada", "âncora final viva; nenhum freeze ou pose morta", GREEN),
    ]
    for i, (tm, t, b, c) in enumerate(timeline):
        y = Inches(1.82 + i * 1.07)
        add_pill(s, Inches(0.68), y + Inches(0.18), Inches(1.62), tm, c, text_color=NAVY, size=10)
        add_card(s, Inches(2.55), y, Inches(9.66), Inches(0.98), t, b, accent=c, title_size=15, body_size=12)
    add_code(s, Inches(0.68), Inches(6.15), Inches(11.55), Inches(0.48),
             "POST /api/generative/h3/compile-prompt   # compila e valida sem reservar GPU", size=11)
    add_phase_rail(s, 2)
    add_notes(s, """
Adapte os tempos à duração real do take. Em FL2VA, o primeiro keyframe fica em 0,00 segundo e o segundo recebe a duração efetiva arredondada para duas casas. Descreva deslocamento, contato, reação e câmera. Evite múltiplas ações incompatíveis no mesmo intervalo. O final deve ter movimento residual, não congelamento.
""")

    # 10
    s = base_slide(prs, "Preflight sem GPU: bloquear erro barato antes do render caro", "CONTROLE", 10)
    checks = [
        ("Identidade", "âncoras, sidecar e negativos", PURPLE),
        ("Física", "contato, peso, direção e reação", CYAN),
        ("Câmera", "eixo, lente, trajetória e estabilidade", BLUE),
        ("Timeline", "beats cobrem toda a duração", GREEN),
        ("Continuidade", "start/end conectam takes vizinhos", YELLOW),
        ("Contrato", "sem freeze, hold, reset ou crossfade", RED),
    ]
    for i, (t, b, c) in enumerate(checks):
        x = Inches(0.62 + (i % 3) * 4.08); y = Inches(1.78 + (i // 3) * 1.78)
        add_card(s, x, y, Inches(3.76), Inches(1.45), t, b, accent=c, number=i+1, title_size=15, body_size=12)
    add_code(s, Inches(0.62), Inches(5.55), Inches(12.02), Inches(0.72),
             "GET /api/video-projects/{project_id}/takes/{take_id}/h3-workflow\n# executa o preflight real e NÃO cria job de GPU", size=11, accent=GREEN)
    add_notes(s, """
Execute o preflight do take antes de enfileirar geração. O endpoint explica o modo H3, as referências, o prompt compilado e os contratos aplicados. Corrija qualquer falha aqui. O objetivo é eliminar rerenders causados por configuração, identidade ou continuidade detectável sem GPU.
""")

    # 11
    s = base_slide(prs, "Fase 4 — geração MiniMax H3 com qualidade preservada", "GERAÇÃO", 11)
    add_card(s, Inches(0.62), Inches(1.85), Inches(3.75), Inches(3.9), "CONFIGURAÇÃO NATIVA",
             "• MiniMax H3 FL2VA\n• Qwen3-VL-32B\n• VAE de vídeo FP16\n• 24 FPS nativos\n• 20 passos de produção\n• seed e resolução registradas", accent=CYAN)
    add_card(s, Inches(4.78), Inches(1.85), Inches(3.75), Inches(3.9), "ANTES DE GERAR",
             "• conferir fila ComfyUI\n• confirmar GPU/VRAM\n• não interromper job alheio\n• prompt e âncoras aprovados\n• duração correta\n• janela pesada autorizada", accent=BLUE)
    add_card(s, Inches(8.94), Inches(1.85), Inches(3.75), Inches(3.9), "NÃO REDUZIR",
             "• steps de produção\n• encoder multimodal\n• sampler\n• resolução para entrega\n• precisão sem A/B\n• qualidade por velocidade", accent=RED)
    add_phase_rail(s, 3)
    add_notes(s, """
O runtime de produção usa a variante pruned INT8 ConvRot validada, com Qwen3-VL e os VAEs fixados. A cadência nativa é 24 FPS. O preview ao vivo é opcional e não muda sampler, encoder, passos, seed, FPS ou arquivo final. SageAttention e qualquer mudança com risco de artefato permanecem em laboratório.
""")

    # 12
    s = base_slide(prs, "Preview ao vivo: observar sem alterar o render", "GERAÇÃO", 12)
    add_round_rect(s, Inches(0.75), Inches(1.95), Inches(5.6), Inches(3.8), fill=PANEL, line=CYAN)
    add_textbox(s, Inches(1.05), Inches(2.25), Inches(5.0), Inches(0.55), "ModelPreviewOverrideKJ", size=23, color=CYAN, bold=True, align=PP_ALIGN.CENTER)
    add_bullets(s, Inches(1.10), Inches(3.05), Inches(4.8), Inches(2.1), [
        "opt-in: desmarcado por padrão",
        "preview máximo 640 px, JPEG 72",
        "um quadro a 12 FPS",
        "não altera o arquivo final",
    ], size=15, color=WHITE, gap=7)
    add_round_rect(s, Inches(6.75), Inches(1.95), Inches(5.6), Inches(3.8), fill=BLACK, line=GREEN)
    add_textbox(s, Inches(7.05), Inches(2.25), Inches(5.0), Inches(0.55), "Contrato preservado", size=23, color=GREEN, bold=True, align=PP_ALIGN.CENTER)
    add_bullets(s, Inches(7.10), Inches(3.05), Inches(4.8), Inches(2.1), [
        "mesmo sampler e guidance",
        "mesmo encoder e seed",
        "mesmos 20 passos",
        "mesma resolução e saída",
    ], size=15, color=WHITE, gap=7)
    add_phase_rail(s, 3)
    add_notes(s, """
Ative o controle Preview ao vivo do H3 apenas quando precisar acompanhar a geração. O node é inserido entre o modelo e os consumidores do guider/scheduler. Se desmarcado, o grafo original é restaurado. Preview não é gate de aprovação; revise o arquivo final e o contact sheet.
""")

    # 13
    s = base_slide(prs, "Fase 5 — aprovação de take no Maestro", "APROVAÇÃO", 13)
    add_card(s, Inches(0.62), Inches(1.75), Inches(3.75), Inches(4.25), "QC TÉCNICO",
             "• duração, FPS e quadros\n• decodificação integral\n• resolução e codec\n• contact sheet\n• arquivo e hash\n• ausência de freeze técnico", accent=BLUE)
    add_card(s, Inches(4.78), Inches(1.75), Inches(3.75), Inches(4.25), "QC VISUAL HUMANO",
             "• identidade e anatomia\n• física do impacto\n• movimento natural\n• cenário e luz\n• câmera e efeitos\n• entrada/saída contínuas", accent=GREEN)
    add_card(s, Inches(8.94), Inches(1.75), Inches(3.75), Inches(4.25), "DECISÃO",
             "APROVAR: segue ao conector\n\nREPROVAR: registrar causa e voltar à etapa correta\n\nNunca autoaprovar", accent=YELLOW)
    add_phase_rail(s, 4)
    add_notes(s, """
No Maestro, o take é candidato até a revisão. Inspecione começo, meio e fim, de preferência em velocidade normal e quadro a quadro nos impactos. Registre a causa da reprovação de forma objetiva: âncora, identidade, anatomia, movimento, física, câmera, cenário ou contrato. Regerar sem corrigir a causa tende a repetir o defeito.
""")

    # 14
    s = base_slide(prs, "Conectores: ação contínua é contrato, não efeito de edição", "CONTINUIDADE", 14)
    # good path
    add_pill(s, Inches(0.72), Inches(1.80), Inches(1.75), "CORRETO", GREEN, text_color=NAVY)
    for i, (txt, c) in enumerate([("fim take A", BLUE), ("FL2VA em ação", CYAN), ("início take B", PURPLE)]):
        x = Inches(0.72 + i * 2.14)
        b = add_round_rect(s, x, Inches(2.35), Inches(1.82), Inches(1.05), fill=PANEL, line=c)
        set_shape_text(b, txt, size=14, color=c, bold=True)
        if i < 2: add_arrow(s, x + Inches(1.84), Inches(2.88), x + Inches(2.10), Inches(2.88), color=GREEN, width=1.6)
    add_pill(s, Inches(7.35), Inches(1.80), Inches(1.75), "PROIBIDO", RED, text_color=WHITE)
    bads = ["crossfade", "freeze", "static hold", "reset/recuo"]
    for i, txt in enumerate(bads):
        x = Inches(7.35 + (i % 2) * 2.42); y = Inches(2.35 + (i // 2) * 1.18)
        b = add_round_rect(s, x, y, Inches(2.12), Inches(0.90), fill=RGBColor(50, 27, 38), line=RED)
        set_shape_text(b, "×  " + txt, size=15, color=RED, bold=True)
    add_round_rect(s, Inches(0.72), Inches(4.55), Inches(5.92), Inches(1.13), fill=BLACK, line=CYAN)
    add_textbox(s, Inches(0.95), Inches(4.74), Inches(5.45), Inches(0.72),
                "1 ação irreversível • movimento útil nos 3 intervalos • final vivo", size=16, color=CYAN, bold=True, align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE)
    add_round_rect(s, Inches(7.35), Inches(4.55), Inches(5.24), Inches(1.13), fill=BLACK, line=RED)
    add_textbox(s, Inches(7.60), Inches(4.74), Inches(4.75), Inches(0.72),
                "crossfade_frames = 0\nfreeze_frames = 0 • static_hold_frames = 0", size=14, color=RED, bold=True, align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE)
    add_phase_rail(s, 4)
    add_notes(s, """
O conector recebe como primeira âncora o último estado útil do take A e como segunda âncora o primeiro estado útil do take B. O prompt descreve uma única ação irreversível que ocupa começo, meio e fim. Se houver congelamento, corte disfarçado ou reinício de golpe, o conector deve ser refeito no MiniMax H3 — não corrigido com crossfade.
""")

    # 15
    s = base_slide(prs, "Picture lock e acabamento: somente material aprovado", "FINALIZAÇÃO", 15)
    steps = [
        ("Picture lock", "ordem e duração fechadas", GREEN),
        ("RIFE 4.6", "24 → 60 FPS", PURPLE),
        ("RealESRGAN", "upscale candidato FHD", BLUE),
        ("NVENC", "H.264 + master", CYAN),
        ("QC", "ffprobe + decodificação", YELLOW),
    ]
    for i, (t, b, c) in enumerate(steps):
        x = Inches(0.58 + i * 2.55)
        add_card(s, x, Inches(2.02), Inches(2.25), Inches(2.60), t, b, accent=c, number=i+1, title_size=15, body_size=12)
        if i < len(steps)-1:
            add_arrow(s, x + Inches(2.26), Inches(3.30), x + Inches(2.50), Inches(3.30), color=MUTED, width=1.4)
    add_round_rect(s, Inches(1.06), Inches(5.15), Inches(11.2), Inches(0.74), fill=PANEL, line=YELLOW)
    add_textbox(s, Inches(1.35), Inches(5.32), Inches(10.62), Inches(0.38),
                "RIFE e upscale não salvam take ruim: identidade, física e continuidade precisam estar aprovadas antes.",
                size=16, color=YELLOW, bold=True, align=PP_ALIGN.CENTER)
    add_phase_rail(s, 5)
    add_notes(s, """
Feche primeiro a montagem a 24 FPS. Interpole em segmentos para 60 FPS com RIFE 4.6 e faça upscale para FHD com RealESRGAN apenas depois da aprovação visual. Encode com FFmpeg/NVENC, meça metadados com ffprobe e decodifique o MP4 integralmente. Preserve o master FHD24 como rollback.
""")

    # 16
    s = base_slide(prs, "Fase 7 — Foley e áudio entram depois do picture lock", "ÁUDIO", 16)
    add_card(s, Inches(0.62), Inches(1.83), Inches(3.6), Inches(3.85), "ENTRADA",
             "vídeo final travado\n\nsem mudança de corte\n\nmapa de eventos sonoros", accent=BLUE)
    add_card(s, Inches(4.42), Inches(1.83), Inches(4.12), Inches(3.85), "HUNYUANVIDEO-FOLEY XXL",
             "gera Foley sincronizado\n\nsaída = candidato\n\nescuta humana obrigatória", accent=ORANGE)
    add_card(s, Inches(8.74), Inches(1.83), Inches(3.96), Inches(3.85), "MASTER DE ÁUDIO",
             "vozes do proprietário\nambiente + impactos\nEBU R128 / true peak\nAAC-LC 48 kHz\nhash e rollback", accent=YELLOW)
    add_phase_rail(s, 6)
    add_notes(s, """
Gere Foley somente quando cortes e durações estiverem fechados; qualquer mudança posterior quebra sincronismo. Escute cada segmento e o master completo. Vozes fornecidas pelo proprietário permanecem separadas e rastreáveis. Meça loudness integrado e pico verdadeiro; depois mux no master de vídeo e valide novamente a decodificação.
""")

    # 17
    s = base_slide(prs, "O que o Maestro expõe ao operador", "MAESTRO", 17)
    endpoints = [
        ("GET /api/generative/status", "estado H3, componentes, skills e prontidão", BLUE),
        ("GET /api/generative/h3/workflow", "diagnóstico completo por origem interna", CYAN),
        ("POST /api/generative/h3/compile-prompt", "compila prompt localmente, sem GPU", PURPLE),
        ("GET .../takes/{take_id}/h3-workflow", "preflight real do take, sem criar job", GREEN),
    ]
    for i, (ep, desc, c) in enumerate(endpoints):
        y = Inches(1.78 + i * 1.08)
        add_code(s, Inches(0.62), y, Inches(5.4), Inches(0.72), ep, size=11, accent=c)
        add_textbox(s, Inches(6.32), y + Inches(0.12), Inches(6.0), Inches(0.42), desc,
                    size=15, color=MUTED, valign=MSO_ANCHOR.MIDDLE)
    add_round_rect(s, Inches(1.28), Inches(6.10), Inches(10.75), Inches(0.45), fill=PANEL, line=CYAN)
    add_textbox(s, Inches(1.52), Inches(6.15), Inches(10.28), Inches(0.28),
                "Painel: Criar › Vídeo › Workflow MiniMax H3 completo: Pronto", size=14, color=CYAN, bold=True, align=PP_ALIGN.CENTER)
    add_notes(s, """
Use o painel para operação comum e os endpoints para diagnóstico. As rotas de workflow são internas e não devem expor ComfyUI diretamente. ComfyUI permanece em 127.0.0.1:8188 e Studio em 127.0.0.1:8029. Um status 'Pronto' significa componentes técnicos presentes; não significa aprovação de um take.
""")

    # 18
    s = base_slide(prs, "Matriz de responsabilidade: quem faz o quê", "GOVERNANÇA", 18)
    # table-like layout
    headers = ["Componente", "Responsabilidade", "Pode aprovar?"]
    xs = [Inches(0.62), Inches(3.55), Inches(10.28)]
    ws = [Inches(2.75), Inches(6.55), Inches(2.36)]
    for x, w, h in zip(xs, ws, headers):
        r = add_round_rect(s, x, Inches(1.72), w, Inches(0.52), fill=CYAN, line=CYAN)
        set_shape_text(r, h, size=13, color=NAVY, bold=True)
    rows = [
        ("Agentes", "planejar, dirigir, validar contratos e documentar", "não"),
        ("Qwen Image", "criar ou reparar fotos âncora", "não"),
        ("MiniMax H3", "gerar takes e conectores", "não"),
        ("RIFE / RealESRGAN", "interpolar e ampliar material aprovado", "não"),
        ("Foley XXL", "gerar áudio sincronizado candidato", "não"),
        ("Proprietário", "aprovar roteiro, âncoras, takes, lock e áudio", "SIM"),
    ]
    for i, row in enumerate(rows):
        y = Inches(2.30 + i * 0.63)
        for j, (x, w, txt) in enumerate(zip(xs, ws, row)):
            fill = RGBColor(25, 44, 72) if i % 2 == 0 else RGBColor(19, 35, 60)
            r = add_round_rect(s, x, y, w, Inches(0.52), fill=fill, line=fill, radius=False)
            set_shape_text(r, txt, size=12, color=GREEN if (i == 5 and j == 2) else WHITE,
                           bold=(i == 5), align=PP_ALIGN.LEFT if j < 2 else PP_ALIGN.CENTER)
    add_notes(s, """
Essa matriz é a fronteira de confiança. Nenhum modelo, agente, teste ou scanner concede aprovação humana. O proprietário pode delegar revisão, mas a decisão deve ficar registrada. Saídas multimodais permanecem candidatas até revisão visual ou auditiva.
""")

    # 19
    s = base_slide(prs, "Outro PC — pré-requisitos antes de restaurar", "RECONSTRUÇÃO", 19)
    reqs = [
        ("Windows 11 x64", "sistema e permissões", BLUE),
        ("NVIDIA + driver", "VRAM adequada ao H3", GREEN),
        ("Python 3.11 x64", "runtime do Studio/ComfyUI", CYAN),
        ("Git + FFmpeg", "ffprobe e h264_nvenc", PURPLE),
        ("Vulkan", "RIFE e aceleração", ORANGE),
        ("Docker Desktop", "runtime Foley XXL", YELLOW),
        ("> 80 GB livres", ">60 GB + reserva de 20 GB", RED),
        ("Rede estável", "downloads retomáveis e hashes", BLUE),
    ]
    for i, (t, b, c) in enumerate(reqs):
        x = Inches(0.62 + (i % 4) * 3.06); y = Inches(1.78 + (i // 4) * 2.04)
        add_card(s, x, y, Inches(2.78), Inches(1.68), t, b, accent=c, title_size=14, body_size=12)
    add_round_rect(s, Inches(1.23), Inches(6.03), Inches(10.86), Inches(0.52), fill=BLACK, line=YELLOW)
    add_textbox(s, Inches(1.48), Inches(6.12), Inches(10.36), Inches(0.30),
                "Modelos não vêm no backup; os BATs baixam, retomam e verificam tudo no PC novo.", size=14, color=YELLOW, bold=True, align=PP_ALIGN.CENTER)
    add_notes(s, """
Antes de copiar o sistema, instale os pré-requisitos e confirme o espaço. O instalador completo preserva 20 GB livres; portanto, não planeje apenas o tamanho bruto dos modelos. Docker Desktop precisa estar operacional para o Foley. O FFmpeg deve expor h264_nvenc.
""")

    # 20
    s = base_slide(prs, "Restauração em outro PC — sequência segura", "RECONSTRUÇÃO", 20)
    steps = [
        "Copiar o ZIP para disco local",
        "Validar SHA-256 externo",
        "Extrair e rodar VALIDAR_BACKUP.ps1",
        "Restaurar em pasta vazia",
        "Criar .env local a partir do exemplo",
        "Diagnosticar PC e instalar modelos",
        "Verificar instalação e listeners",
        "Compilar prompt + preflight de teste",
    ]
    for i, txt in enumerate(steps):
        x = Inches(0.62 + (i % 2) * 6.12); y = Inches(1.72 + (i // 2) * 1.14)
        add_card(s, x, y, Inches(5.78), Inches(0.90), txt, None,
                 accent=CYAN if i < 4 else GREEN, number=i+1, title_size=13)
    add_notes(s, """
Nunca restaure sobre uma árvore ativa desconhecida. O destino deve estar vazio. Valide primeiro o pacote e depois a instalação. Crie o .env localmente e nunca transporte credenciais dentro do backup. Só inicie inferência pesada depois que listeners, componentes, testes e preflight passarem.
""")

    # 21
    s = base_slide(prs, "Comandos essenciais da reconstrução", "RECONSTRUÇÃO", 21)
    add_code(s, Inches(0.62), Inches(1.72), Inches(12.05), Inches(0.80),
             "powershell -ExecutionPolicy Bypass -File .\\VALIDAR_BACKUP.ps1", size=14, accent=BLUE)
    add_code(s, Inches(0.62), Inches(2.72), Inches(12.05), Inches(0.80),
             "powershell -ExecutionPolicy Bypass -File .\\RESTAURAR_PC_NOVO.ps1 -TargetRoot E:\\Pemara", size=14, accent=PURPLE)
    add_code(s, Inches(0.62), Inches(3.72), Inches(12.05), Inches(0.80),
             ".\\INSTALAR_MODELOS\\00_DIAGNOSTICAR_PC.bat\n.\\INSTALAR_MODELOS\\INSTALAR_TUDO_MODELOS.bat", size=13, accent=CYAN)
    add_code(s, Inches(0.62), Inches(4.72), Inches(12.05), Inches(0.80),
             ".\\INSTALAR_MODELOS\\VERIFICAR_MODELOS.bat\npowershell -ExecutionPolicy Bypass -File .\\VALIDAR_INSTALACAO.ps1 -RequireModels", size=12, accent=GREEN)
    add_round_rect(s, Inches(1.65), Inches(5.90), Inches(10.02), Inches(0.50), fill=PANEL, line=YELLOW)
    add_textbox(s, Inches(1.90), Inches(5.99), Inches(9.55), Inches(0.29),
                "Ajuste o caminho apenas quando o destino real for diferente — nunca chute a raiz.", size=13, color=YELLOW, bold=True, align=PP_ALIGN.CENTER)
    add_notes(s, """
Execute os comandos a partir da raiz extraída. Se o sistema for restaurado em outra unidade, defina PEMARA_ROOT antes do instalador. Use ExecutionPolicy Bypass apenas por processo; não altere permanentemente a política do Windows. Qualquer divergência de hash bloqueia a sequência.
""")

    # 22
    s = base_slide(prs, "Instaladores pesados: ordem, retomada e dry-run", "RECONSTRUÇÃO", 22)
    installers = [
        ("01", "H3 + VAEs", "FL2VA pruned INT8 ConvRot", CYAN),
        ("02", "Qwen H3", "Qwen3-VL-32B NVFP4/AWQ", BLUE),
        ("03", "FHD60", "RIFE 4.6 + RealESRGAN x2", PURPLE),
        ("04", "Foley XXL", "pesos + Docker runtime", ORANGE),
    ]
    for i, (n, t, b, c) in enumerate(installers):
        x = Inches(0.62 + i * 3.04)
        add_card(s, x, Inches(1.78), Inches(2.77), Inches(2.50), t, b, accent=c, number=n, title_size=15, body_size=12)
    add_code(s, Inches(0.62), Inches(4.72), Inches(5.82), Inches(1.02),
             "set PEMARA_NO_PAUSE=1\nINSTALAR_TUDO_MODELOS.bat --dry-run", size=13, accent=YELLOW)
    add_code(s, Inches(6.84), Inches(4.72), Inches(5.82), Inches(1.02),
             "set PEMARA_ROOT=D:\\Pemara\nINSTALAR_TUDO_MODELOS.bat", size=13, accent=GREEN)
    add_textbox(s, Inches(0.72), Inches(6.04), Inches(11.9), Inches(0.38),
                "Segunda execução: artefatos já verificados são pulados; downloads interrompidos são retomados.", size=14, color=MUTED, align=PP_ALIGN.CENTER)
    add_notes(s, """
Use --dry-run para validar planejamento, caminhos e espaço sem baixar. O models.lock.json trava fontes, revisões, tamanhos e SHA-256. O instalador não grava token no manifesto ou logs. Ao executar os BATs, o proprietário confirma as licenças comunitárias MiniMax H3 e Tencent Hunyuan.
""")

    # 23
    s = base_slide(prs, "Diagnóstico: onde agir quando algo falha", "SUPORTE", 23)
    problems = [
        ("Workflow não está Pronto", "rodar diagnóstico → verificar modelos → validar instalação", RED),
        ("Take alucina identidade", "parar rerender → refazer âncora → recompilar prompt", PURPLE),
        ("Conector congela", "reprovar → FL2VA start/end → ação irreversível", CYAN),
        ("Sem NVENC", "driver/FFmpeg → conferir h264_nvenc", BLUE),
        ("Foley não inicia", "Docker Desktop → imagem/pesos → verificar runtime", ORANGE),
        ("Hash diverge", "bloquear → quarentena → baixar/restaurar novamente", YELLOW),
    ]
    for i, (t, b, c) in enumerate(problems):
        x = Inches(0.62 + (i % 2) * 6.12); y = Inches(1.72 + (i // 2) * 1.45)
        add_card(s, x, y, Inches(5.78), Inches(1.18), t, b, accent=c, title_size=14, body_size=11)
    add_round_rect(s, Inches(1.46), Inches(6.18), Inches(10.42), Inches(0.42), fill=BLACK, line=RED)
    add_textbox(s, Inches(1.70), Inches(6.23), Inches(9.94), Inches(0.28),
                "Não mascarar causa-raiz com edição, redução de qualidade ou reinício cego.", size=13, color=RED, bold=True, align=PP_ALIGN.CENTER)
    add_notes(s, """
O diagnóstico sempre começa no componente que define o defeito. Identidade vem das âncoras; movimento vem do prompt/contrato; freeze vem do conector; codec vem do ambiente; Foley vem do Docker e dos pesos. Preserve logs e candidatos reprovados até a substituição passar pelos mesmos gates.
""")

    # 24
    s = base_slide(prs, "Checklist de aceite — pronto para produzir", "ENCERRAMENTO", 24)
    left = [
        "roteiro e continuidade aprovados",
        "âncoras start/end aprovadas",
        "prompt oficial compilado",
        "preflight do take passou",
        "fila/GPU verificadas",
        "takes e conectores aprovados",
    ]
    right = [
        "zero crossfade/freeze/hold/reset",
        "picture lock fechado",
        "FHD60 validado e rollback FHD24",
        "Foley e vozes aprovados",
        "loudness, hashes e decodificação PASS",
        "backup restaurável e privado",
    ]
    add_card(s, Inches(0.62), Inches(1.72), Inches(5.78), Inches(4.63), "PRODUÇÃO",
             "\n".join("✓ " + x for x in left), accent=CYAN, title_size=18, body_size=14)
    add_card(s, Inches(6.82), Inches(1.72), Inches(5.78), Inches(4.63), "ENTREGA",
             "\n".join("✓ " + x for x in right), accent=GREEN, title_size=18, body_size=14)
    add_round_rect(s, Inches(2.37), Inches(6.52), Inches(8.58), Inches(0.42), fill=CYAN, line=CYAN)
    add_textbox(s, Inches(2.60), Inches(6.56), Inches(8.12), Inches(0.28),
                "Qualidade é uma sequência de decisões corretas — não um único botão.", size=14, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
    add_notes(s, """
Use este slide como gate final de reunião. Nenhum item pode ser presumido. O PASS técnico confirma integridade e funcionamento; a aprovação do proprietário confirma imagem e áudio. Guarde o master final, o rollback, hashes, relatórios e documentação do workflow.
""")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT)
    return OUT, len(prs.slides)


if __name__ == "__main__":
    path, count = build_deck()
    print(f"PPTX={path}")
    print(f"SLIDES={count}")
