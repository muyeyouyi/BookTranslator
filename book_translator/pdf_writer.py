from html import escape
from pathlib import Path

from loguru import logger
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from book_translator.document_content import (
    MARGIN, PAGE_HEIGHT, PAGE_WIDTH, SCAN_NOTICE, column_widths, fit_image,
    image_path, inline_spans, text_parts,
)


def register_chinese_font(configured=None):
    candidates = [configured] if configured else [
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        Path("/System/Library/Fonts/STHeiti Light.ttc"),
        Path("C:/Windows/Fonts/simsun.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            try:
                import hashlib
                name = "BookChinese_" + hashlib.sha256(str(candidate).encode()).hexdigest()[:12]
                if name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(name, str(candidate), subfontIndex=0))
                pdfmetrics.registerFontFamily(name, normal=name, bold=name, italic=name, boldItalic=name)
                return name
            except Exception:
                if configured:
                    raise ValueError("无法加载指定的 PDF 字体，请使用包含 TrueType 字形的 TTF/TTC 字体") from None
    name = "STSong-Light"
    if name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(name))
    pdfmetrics.registerFontFamily(name, normal=name, bold=name, italic=name, boldItalic=name)
    logger.warning("未找到可嵌入中文字体，使用 STSong-Light；可通过 --pdf-font 指定字体以改善跨设备显示")
    return name


class PDFWriter:
    """使用原子替换发布排版后的中文 PDF；原输入文件保持不变。"""

    def __init__(self, path, title, extract_only=False, font_path=None):
        self.path, self.title = path, title
        font = register_chinese_font(font_path)
        self.body = ParagraphStyle("BookBody", fontName=font, fontSize=11, leading=17,
                                   wordWrap="CJK", spaceAfter=8, splitLongWords=True)
        self.heading = ParagraphStyle("BookHeading", parent=self.body, fontSize=15, leading=21, spaceBefore=10, keepWithNext=True)
        self.title_style = ParagraphStyle("BookTitle", parent=self.body, fontSize=22, leading=28, spaceAfter=18)
        self.cell_style = ParagraphStyle("BookCell", parent=self.body, fontSize=10, leading=14, spaceAfter=0)
        self.story = [Paragraph(escape(title), self.title_style)]
        if extract_only:
            self.story.append(Paragraph("本地提取预览，尚未翻译", self.body))
        self.page_count = 0

    def _paragraph(self, text, style=None, literal=False):
        if literal:
            formatted = escape(text)
        else:
            tags = {"bold": "b", "italic": "i"}
            formatted = "".join(f"<{tags[kind]}>{escape(value)}</{tags[kind]}>" if kind in tags else escape(value)
                                for value, kind in inline_spans(text))
        return Paragraph(formatted.replace("\n", "<br/>"), style or self.body)

    def add_page(self, page):
        if self.page_count:
            self.story.append(PageBreak())
        self.page_count += 1
        if not page.has_text:
            self.story.append(self._paragraph(SCAN_NOTICE))
        for block in page.blocks:
            if block.kind == "image":
                path = image_path(self.path, block.image_path)
                width, height = fit_image(path)
                self.story.extend([Image(str(path), width=width, height=height), Spacer(1, 10)])
            elif block.kind == "table" and block.rows and any(block.rows):
                widths = column_widths(block.rows)
                rows = [[self._paragraph(str(cell), self.cell_style) for cell in row] +
                        [self._paragraph("", self.cell_style)] * (len(widths) - len(row)) for row in block.rows]
                table = LongTable(rows, colWidths=widths, repeatRows=1, splitByRow=1, splitInRow=1)
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9EEF3")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9D9D9")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]))
                self.story.extend([table, Spacer(1, 12)])
            else:
                for kind, text, level in text_parts(block.text):
                    self.story.append(self._paragraph(text, self.heading if kind == "heading" else self.body, kind == "code"))

    def finish(self):
        if not self.page_count:
            raise ValueError("没有可输出的页面")
        temporary = self.path.with_suffix(".partial.pdf")
        try:
            SimpleDocTemplate(str(temporary), pagesize=(PAGE_WIDTH, PAGE_HEIGHT),
                              leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=MARGIN,
                              title=self.title, author="").build(self.story)
            temporary.replace(self.path)
        finally:
            temporary.unlink(missing_ok=True)
        return self.path
