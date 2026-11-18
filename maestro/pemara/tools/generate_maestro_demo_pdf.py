from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "docs" / "demonstracao" / "MAESTRO_WORKFLOW_DEMONSTRACAO_20260818.md"
DEFAULT_OUTPUT = ROOT / "docs" / "demonstracao" / "MAESTRO_PRO_WORKFLOW_COMPLETO_DEMONSTRACAO_20260818.pdf"
LOGO = ROOT / "app" / "assets" / "brand" / "pemara-tech-logo.png"

NAVY = colors.HexColor("#07162A")
BLUE = colors.HexColor("#0A4F9C")
CYAN = colors.HexColor("#1CA6D9")
ORANGE = colors.HexColor("#FF8A00")
LIGHT_ORANGE = colors.HexColor("#FFF2DE")
LIGHT_BLUE = colors.HexColor("#EAF4FC")
LIGHT_GRAY = colors.HexColor("#F3F5F7")
MID_GRAY = colors.HexColor("#687587")
TEXT = colors.HexColor("#172033")
GREEN = colors.HexColor("#178A55")
RED = colors.HexColor("#B63B3B")
WHITE = colors.white


def register_fonts() -> None:
    candidates = {
        "PemaraSans": [Path(r"C:\Windows\Fonts\segoeui.ttf"), Path(r"C:\Windows\Fonts\arial.ttf")],
        "PemaraSans-Bold": [Path(r"C:\Windows\Fonts\segoeuib.ttf"), Path(r"C:\Windows\Fonts\arialbd.ttf")],
        "PemaraMono": [Path(r"C:\Windows\Fonts\consola.ttf"), Path(r"C:\Windows\Fonts\cour.ttf")],
    }
    for name, paths in candidates.items():
        selected = next((path for path in paths if path.exists()), None)
        if selected is None:
            continue
        pdfmetrics.registerFont(TTFont(name, str(selected)))
    pdfmetrics.registerFontFamily(
        "PemaraSans",
        normal="PemaraSans",
        bold="PemaraSans-Bold",
        italic="PemaraSans",
        boldItalic="PemaraSans-Bold",
    )


def styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "body": ParagraphStyle(
            "Body",
            parent=sample["BodyText"],
            fontName="PemaraSans",
            fontSize=9.2,
            leading=13.2,
            textColor=TEXT,
            spaceAfter=6,
            alignment=TA_LEFT,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=sample["Heading1"],
            fontName="PemaraSans-Bold",
            fontSize=19,
            leading=23,
            textColor=NAVY,
            spaceBefore=9,
            spaceAfter=10,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=sample["Heading2"],
            fontName="PemaraSans-Bold",
            fontSize=13.5,
            leading=17,
            textColor=BLUE,
            spaceBefore=9,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=sample["Heading3"],
            fontName="PemaraSans-Bold",
            fontSize=10.5,
            leading=13,
            textColor=colors.HexColor("#0E6D93"),
            spaceBefore=6,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "quote": ParagraphStyle(
            "Quote",
            parent=sample["BodyText"],
            fontName="PemaraSans",
            fontSize=10,
            leading=14.2,
            leftIndent=12,
            rightIndent=8,
            borderColor=ORANGE,
            borderWidth=0,
            borderPadding=(8, 10, 8, 12),
            backColor=LIGHT_ORANGE,
            textColor=NAVY,
            spaceBefore=5,
            spaceAfter=9,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=sample["BodyText"],
            fontName="PemaraSans",
            fontSize=9,
            leading=12.5,
            textColor=TEXT,
            leftIndent=0,
            spaceAfter=2,
        ),
        "table": ParagraphStyle(
            "TableCell",
            parent=sample["BodyText"],
            fontName="PemaraSans",
            fontSize=7.4,
            leading=9.4,
            textColor=TEXT,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=sample["BodyText"],
            fontName="PemaraSans-Bold",
            fontSize=7.5,
            leading=9.4,
            textColor=WHITE,
        ),
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=sample["Title"],
            fontName="PemaraSans-Bold",
            fontSize=31,
            leading=35,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=7,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=sample["BodyText"],
            fontName="PemaraSans",
            fontSize=15,
            leading=20,
            textColor=BLUE,
            alignment=TA_LEFT,
        ),
        "cover_meta": ParagraphStyle(
            "CoverMeta",
            parent=sample["BodyText"],
            fontName="PemaraSans",
            fontSize=9.5,
            leading=13,
            textColor=MID_GRAY,
            alignment=TA_LEFT,
        ),
    }


def inline_markup(value: str) -> str:
    value = html.escape(value.strip(), quote=False)
    value = re.sub(
        r"\[([^\]]+)\]\((https?://[^)]+)\)",
        r'<link href="\2" color="#0A4F9C"><u>\1</u></link>',
        value,
    )
    value = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"`([^`]+)`", r'<font name="PemaraMono" size="8">\1</font>', value)
    return value


class ArchitectureDiagram(Flowable):
    def __init__(self, width: float):
        super().__init__()
        self.width = width
        self.height = 285

    def draw_box(self, canvas, x, y, w, h, title, subtitle, fill, line=BLUE):
        canvas.setFillColor(fill)
        canvas.setStrokeColor(line)
        canvas.setLineWidth(1)
        canvas.roundRect(x, y, w, h, 7, fill=1, stroke=1)
        canvas.setFillColor(NAVY)
        canvas.setFont("PemaraSans-Bold", 9)
        canvas.drawCentredString(x + w / 2, y + h - 16, title)
        canvas.setFillColor(MID_GRAY)
        canvas.setFont("PemaraSans", 7.2)
        for index, line_text in enumerate(subtitle.split("\n")):
            canvas.drawCentredString(x + w / 2, y + h - 30 - index * 10, line_text)

    def arrow(self, canvas, x1, y1, x2, y2):
        canvas.setStrokeColor(CYAN)
        canvas.setFillColor(CYAN)
        canvas.setLineWidth(1.5)
        canvas.line(x1, y1, x2, y2)
        angle = 5
        if abs(x2 - x1) > abs(y2 - y1):
            direction = 1 if x2 > x1 else -1
            canvas.line(x2, y2, x2 - direction * angle, y2 + 3)
            canvas.line(x2, y2, x2 - direction * angle, y2 - 3)
        else:
            direction = 1 if y2 > y1 else -1
            canvas.line(x2, y2, x2 - 3, y2 - direction * angle)
            canvas.line(x2, y2, x2 + 3, y2 - direction * angle)

    def draw(self):
        c = self.canv
        w = self.width
        top_w, top_h = 210, 48
        top_x = (w - top_w) / 2
        self.draw_box(c, top_x, 224, top_w, top_h, "MAESTRO WEB", "login • projetos • revisão • aprovação", LIGHT_ORANGE, ORANGE)
        mid_w, mid_h = 205, 52
        mid_x = (w - mid_w) / 2
        self.arrow(c, w / 2, 224, w / 2, 206)
        self.draw_box(c, mid_x, 150, mid_w, mid_h, "STUDIO FASTAPI", "jobs • contratos • readiness • APIs", LIGHT_BLUE)
        self.arrow(c, w / 2, 150, w / 2, 132)
        gap = 10
        box_w = (w - gap * 3) / 4
        xs = [gap + i * (box_w + gap) for i in range(4)]
        boxes = [
            ("COMFYUI", "fila única\n127.0.0.1:8188", LIGHT_BLUE),
            ("MODELOS", "H3 • Qwen\nRTX 5090", LIGHT_ORANGE),
            ("ÁUDIO", "Foley • LeVo 2\nrevisão humana", colors.HexColor("#EAF8F1")),
            ("ACABAMENTO", "FFmpeg • RIFE\nRealESRGAN", LIGHT_GRAY),
        ]
        for x, (title, subtitle, fill) in zip(xs, boxes):
            self.draw_box(c, x, 67, box_w, 58, title, subtitle, fill)
            self.arrow(c, w / 2, 132, x + box_w / 2, 125)
        c.setFillColor(NAVY)
        c.roundRect(10, 8, w - 20, 39, 7, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("PemaraSans-Bold", 8.5)
        c.drawCentredString(w / 2, 31, "GOVERNANÇA TRANSVERSAL")
        c.setFont("PemaraSans", 7.3)
        c.drawCentredString(w / 2, 18, "skills seletivas • QC • aprovação do proprietário • hashes • backup • rollback")


class WorkflowDiagram(Flowable):
    def __init__(self, width: float):
        super().__init__()
        self.width = width
        self.height = 505
        self.stages = [
            ("1", "Roteiro e contrato", "aprovação do roteiro"),
            ("2", "Fotos-âncora", "aprovação visual"),
            ("3", "Prompt H3 oficial", "contrato íntegro"),
            ("4", "Preflight sem GPU", "fail-closed"),
            ("5", "Geração H3", "candidato técnico"),
            ("6", "QC visual", "aprovação humana"),
            ("7", "Conectores contínuos", "zero freeze/reset"),
            ("8", "Picture lock FHD60", "preserva nativo"),
            ("9", "Foley", "escuta humana"),
            ("10", "Master e rollback", "aprovação final"),
        ]

    def draw_stage(self, c, x, y, w, h, number, title, gate, active=False):
        fill = LIGHT_ORANGE if active else LIGHT_BLUE
        stroke = ORANGE if active else BLUE
        c.setFillColor(fill)
        c.setStrokeColor(stroke)
        c.setLineWidth(1)
        c.roundRect(x, y, w, h, 7, fill=1, stroke=1)
        c.setFillColor(stroke)
        c.circle(x + 18, y + h / 2, 11, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("PemaraSans-Bold", 8.5)
        c.drawCentredString(x + 18, y + h / 2 - 3, number)
        c.setFillColor(NAVY)
        c.setFont("PemaraSans-Bold", 8.5)
        c.drawString(x + 36, y + h - 17, title)
        c.setFillColor(MID_GRAY)
        c.setFont("PemaraSans", 7)
        c.drawString(x + 36, y + 10, gate)

    def arrow_down(self, c, x, y1, y2):
        c.setStrokeColor(CYAN)
        c.setFillColor(CYAN)
        c.setLineWidth(1.4)
        c.line(x, y1, x, y2)
        c.line(x, y2, x - 3, y2 + 5)
        c.line(x, y2, x + 3, y2 + 5)

    def draw(self):
        c = self.canv
        gap = 24
        col_w = (self.width - gap) / 2
        box_h = 64
        row_gap = 27
        start_y = self.height - box_h - 8
        for col in range(2):
            x = col * (col_w + gap)
            for row in range(5):
                index = col * 5 + row
                number, title, gate = self.stages[index]
                y = start_y - row * (box_h + row_gap)
                self.draw_stage(c, x, y, col_w, box_h, number, title, gate, active=index in {4, 8, 9})
                if row < 4:
                    self.arrow_down(c, x + col_w / 2, y, y - row_gap + 5)
        left_end_y = start_y - 4 * (box_h + row_gap) + box_h / 2
        right_start_y = start_y + box_h / 2
        c.setStrokeColor(CYAN)
        c.setLineWidth(1.4)
        c.line(col_w, left_end_y, col_w + gap / 2, left_end_y)
        c.line(col_w + gap / 2, left_end_y, col_w + gap / 2, right_start_y)
        c.line(col_w + gap / 2, right_start_y, col_w + gap, right_start_y)
        c.setFillColor(CYAN)
        c.line(col_w + gap, right_start_y, col_w + gap - 5, right_start_y + 3)
        c.line(col_w + gap, right_start_y, col_w + gap - 5, right_start_y - 3)


class ApprovalDiagram(Flowable):
    def __init__(self, width: float):
        super().__init__()
        self.width = width
        self.height = 230

    def box(self, c, x, y, w, h, title, subtitle, fill, stroke):
        c.setFillColor(fill)
        c.setStrokeColor(stroke)
        c.roundRect(x, y, w, h, 7, fill=1, stroke=1)
        c.setFillColor(NAVY)
        c.setFont("PemaraSans-Bold", 8.5)
        c.drawCentredString(x + w / 2, y + h - 17, title)
        c.setFillColor(MID_GRAY)
        c.setFont("PemaraSans", 6.8)
        c.drawCentredString(x + w / 2, y + 10, subtitle)

    def arrow(self, c, x1, y1, x2, y2, color=CYAN):
        c.setStrokeColor(color)
        c.setFillColor(color)
        c.setLineWidth(1.4)
        c.line(x1, y1, x2, y2)
        c.line(x2, y2, x2 - 5, y2 + 3)
        c.line(x2, y2, x2 - 5, y2 - 3)

    def draw(self):
        c = self.canv
        w = self.width
        box_w = 125
        y = 140
        xs = [0, (w - box_w) / 2, w - box_w]
        self.box(c, xs[0], y, box_w, 58, "CANDIDATO IA", "nunca aprovado sozinho", LIGHT_BLUE, BLUE)
        self.box(c, xs[1], y, box_w, 58, "QC TÉCNICO", "evidência e bloqueios", LIGHT_ORANGE, ORANGE)
        self.box(c, xs[2], y, box_w, 58, "PROPRIETÁRIO", "aprovar ou reprovar", colors.HexColor("#EAF8F1"), GREEN)
        self.arrow(c, xs[0] + box_w, y + 29, xs[1], y + 29)
        self.arrow(c, xs[1] + box_w, y + 29, xs[2], y + 29)
        result_w = 150
        self.box(c, 35, 32, result_w, 55, "REPROVADO", "motivo preservado; nova iteração", colors.HexColor("#FCECEC"), RED)
        self.box(c, w - 35 - result_w, 32, result_w, 55, "APROVADO", "elegível para a próxima etapa", colors.HexColor("#EAF8F1"), GREEN)
        c.setStrokeColor(RED)
        c.line(xs[2] + box_w / 2, y, 110, 87)
        c.setStrokeColor(GREEN)
        c.line(xs[2] + box_w / 2, y, w - 110, 87)
        c.setFillColor(MID_GRAY)
        c.setFont("PemaraSans", 7.2)
        c.drawCentredString(w / 2, 8, "Sucesso técnico e aprovação artística são estados diferentes.")


def table_widths(rows: list[list[str]], total_width: float) -> list[float]:
    columns = len(rows[0])
    weights = []
    for col in range(columns):
        longest = max(len(re.sub(r"<[^>]+>", "", row[col])) for row in rows)
        weights.append(min(max(longest, 12), 42))
    weight_sum = sum(weights)
    widths = [total_width * weight / weight_sum for weight in weights]
    minimum = 70
    if columns <= 4:
        widths = [max(minimum, width) for width in widths]
        scale = total_width / sum(widths)
        widths = [width * scale for width in widths]
    return widths


def build_table(raw_rows: list[list[str]], style_map: dict[str, ParagraphStyle], total_width: float) -> Table:
    formatted = []
    for row_index, row in enumerate(raw_rows):
        paragraph_style = style_map["table_header"] if row_index == 0 else style_map["table"]
        formatted.append([Paragraph(inline_markup(cell), paragraph_style) for cell in row])
    table = Table(formatted, colWidths=table_widths(raw_rows, total_width), repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD4DD")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def parse_markdown(text: str, style_map: dict[str, ParagraphStyle], content_width: float) -> list[Flowable]:
    marker = "[[PAGEBREAK]]"
    if marker in text:
        text = text.split(marker, 1)[1]
    lines = text.splitlines()
    story: list[Flowable] = []
    paragraph: list[str] = []
    bullets: list[str] = []
    quote: list[str] = []
    index = 0

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            story.append(Paragraph(inline_markup(" ".join(part.strip() for part in paragraph)), style_map["body"]))
            paragraph = []

    def flush_bullets() -> None:
        nonlocal bullets
        if bullets:
            items = [ListItem(Paragraph(inline_markup(item), style_map["bullet"]), leftIndent=8) for item in bullets]
            story.append(ListFlowable(items, bulletType="bullet", start="circle", leftIndent=18, bulletFontName="PemaraSans", bulletFontSize=6, spaceAfter=6))
            bullets = []

    def flush_quote() -> None:
        nonlocal quote
        if quote:
            story.append(Paragraph(inline_markup(" ".join(quote)), style_map["quote"]))
            quote = []

    def flush_all() -> None:
        flush_paragraph()
        flush_bullets()
        flush_quote()

    while index < len(lines):
        raw = lines[index]
        line = raw.strip()
        if line.startswith("|") and line.endswith("|"):
            flush_all()
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|") and lines[index].strip().endswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            rows = [[cell.strip() for cell in table_line.strip("|").split("|")] for table_line in table_lines]
            rows = [row for row in rows if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in row)]
            story.append(build_table(rows, style_map, content_width))
            story.append(Spacer(1, 7))
            continue
        if line == "[[PAGEBREAK]]":
            flush_all()
            story.append(PageBreak())
        elif line == "[[DIAGRAM:ARCHITECTURE]]":
            flush_all()
            story.append(ArchitectureDiagram(content_width))
            story.append(Spacer(1, 8))
        elif line == "[[DIAGRAM:WORKFLOW]]":
            flush_all()
            story.append(WorkflowDiagram(content_width))
            story.append(Spacer(1, 8))
        elif line == "[[DIAGRAM:APPROVAL]]":
            flush_all()
            story.append(ApprovalDiagram(content_width))
            story.append(Spacer(1, 8))
        elif line.startswith("### "):
            flush_all()
            story.append(Paragraph(inline_markup(line[4:]), style_map["h3"]))
        elif line.startswith("## "):
            flush_all()
            story.append(Paragraph(inline_markup(line[3:]), style_map["h2"]))
        elif line.startswith("# "):
            flush_all()
            story.append(Paragraph(inline_markup(line[2:]), style_map["h1"]))
            story.append(HRFlowable(width="100%", thickness=1.2, color=ORANGE, spaceAfter=7))
        elif line.startswith("> "):
            flush_paragraph()
            flush_bullets()
            quote.append(line[2:].strip())
        elif re.match(r"^-\s+", line):
            flush_paragraph()
            flush_quote()
            bullets.append(re.sub(r"^-\s+", "", line))
        elif re.match(r"^\d+\.\s+", line):
            flush_paragraph()
            flush_quote()
            bullets.append(re.sub(r"^\d+\.\s+", "", line))
        elif not line:
            flush_all()
        else:
            flush_bullets()
            flush_quote()
            paragraph.append(line)
        index += 1
    flush_all()
    return story


def cover_story(style_map: dict[str, ParagraphStyle]) -> list[Flowable]:
    logo = Image(str(LOGO), width=165 * mm, height=94.7 * mm)
    logo.hAlign = "LEFT"
    return [
        Spacer(1, 3 * mm),
        logo,
        Spacer(1, 7 * mm),
        HRFlowable(width="100%", thickness=4, color=ORANGE, spaceAfter=10),
        Paragraph("MAESTRO PRO", style_map["cover_title"]),
        Paragraph("Workflow completo, arquitetura e inventário demonstrativo", style_map["cover_subtitle"]),
        Spacer(1, 10 * mm),
        Table(
            [[Paragraph("PRODUÇÃO MULTIMODAL LOCAL", style_map["table_header"])]],
            colWidths=[83 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                    ("BOX", (0, 0), (-1, -1), 0, NAVY),
                    ("LEFTPADDING", (0, 0), (-1, -1), 9),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            ),
            hAlign="LEFT",
        ),
        Spacer(1, 7 * mm),
        Paragraph("MiniMax H3 · Qwen · ComfyUI · Foley · QC humano · montagem segura · backup verificável", style_map["cover_meta"]),
        Spacer(1, 10 * mm),
        Paragraph("Pemara Tech · 18 de agosto de 2026", style_map["cover_meta"]),
        PageBreak(),
    ]


def page_decor(canvas, doc) -> None:
    page = canvas.getPageNumber()
    canvas.saveState()
    if page > 1:
        canvas.setStrokeColor(colors.HexColor("#D7DEE6"))
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, A4[1] - 16 * mm, A4[0] - doc.rightMargin, A4[1] - 16 * mm)
        canvas.setFont("PemaraSans-Bold", 7.5)
        canvas.setFillColor(BLUE)
        canvas.drawString(doc.leftMargin, A4[1] - 12.7 * mm, "PEMARA TECH · MAESTRO PRO")
        canvas.setFont("PemaraSans", 7.2)
        canvas.setFillColor(MID_GRAY)
        canvas.drawRightString(A4[0] - doc.rightMargin, A4[1] - 12.7 * mm, "Documento demonstrativo · 18/08/2026")
        canvas.setStrokeColor(colors.HexColor("#D7DEE6"))
        canvas.line(doc.leftMargin, 14 * mm, A4[0] - doc.rightMargin, 14 * mm)
        canvas.setFont("PemaraSans", 7.3)
        canvas.drawString(doc.leftMargin, 9.5 * mm, "IA produz candidatos; o proprietário aprova.")
        canvas.drawRightString(A4[0] - doc.rightMargin, 9.5 * mm, f"Página {page}")
    canvas.restoreState()


def generate(source: Path, output: Path) -> None:
    register_fonts()
    style_map = styles()
    output.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=21 * mm,
        bottomMargin=19 * mm,
        title="Maestro Pro — Workflow completo, arquitetura e inventário demonstrativo",
        author="Pemara Tech",
        subject="Documentação técnica e executiva do Maestro Pro",
        creator="Maestro Pro / Codex",
    )
    content_width = A4[0] - document.leftMargin - document.rightMargin
    text = source.read_text(encoding="utf-8")
    story = cover_story(style_map)
    story.extend(parse_markdown(text, style_map, content_width))
    document.build(story, onFirstPage=page_decor, onLaterPages=page_decor)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera o PDF demonstrativo do Maestro Pro.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    generate(args.source.resolve(), args.output.resolve())
    print(args.output.resolve())


if __name__ == "__main__":
    main()
