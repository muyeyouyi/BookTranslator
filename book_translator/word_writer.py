import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

from book_translator.document_content import (
    MARGIN, PAGE_HEIGHT, PAGE_WIDTH, SCAN_NOTICE, column_widths,
    fit_image, image_path, inline_spans, text_parts,
)


class WordWriter:
    """生成含可编辑正文、原生表格及嵌入图片的 DOCX。"""

    def __init__(self, path, title, extract_only=False):
        self.path = path
        self.document = Document()
        self.chinese_font = "Arial Unicode MS" if sys.platform == "darwin" and Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf").is_file() else "SimSun"
        self.document.core_properties.title = title
        self.document.core_properties.author = ""
        section = self.document.sections[0]
        section.page_width, section.page_height = Pt(PAGE_WIDTH), Pt(PAGE_HEIGHT)
        section.top_margin = section.bottom_margin = section.left_margin = section.right_margin = Pt(MARGIN)
        for name in ["Normal", "Title", "Heading 1", "Heading 2", "Heading 3"]:
            style = self.document.styles[name]
            style.font.name = "Arial"
            style.font.color.rgb = RGBColor(0, 0, 0)
            fonts = style.element.get_or_add_rPr().get_or_add_rFonts()
            for attribute in list(fonts.attrib):
                if "theme" in attribute.lower():
                    del fonts.attrib[attribute]
            fonts.set(qn("w:eastAsia"), self.chinese_font)
            # 清除模板残留的标题装饰线，避免不同模板/阅读器改变版面。
            for border in list(style.element.iter(qn("w:pBdr"))):
                border.getparent().remove(border)
        normal = self.document.styles["Normal"]
        normal.font.size = Pt(11)
        normal.paragraph_format.line_spacing = 1.4
        normal.paragraph_format.space_after = Pt(8)
        self._fill(self.document.add_paragraph(style="Title"), title)
        if extract_only:
            self._fill(self.document.add_paragraph(), "本地提取预览，尚未翻译")
        self.page_count = 0

    def _fill(self, paragraph, text, literal=False):
        for value, kind in ([(text, "code")] if literal else inline_spans(text)):
            run = paragraph.add_run(value)
            run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), self.chinese_font)
            run.bold = kind == "bold"
            run.italic = kind == "italic"
            if kind == "code":
                run.font.name = "Courier New"

    def add_page(self, page):
        if self.page_count:
            # 使用段前分页；独立的分页符段落在表格恰好填满页面时可能产生空白页。
            boundary = self.document.add_paragraph()
            boundary.paragraph_format.page_break_before = True
            boundary.paragraph_format.space_before = Pt(0)
            boundary.paragraph_format.space_after = Pt(0)
            boundary.paragraph_format.line_spacing = Pt(1)
            boundary.add_run().font.size = Pt(1)
        self.page_count += 1
        if not page.has_text:
            self._fill(self.document.add_paragraph(), SCAN_NOTICE)
        for block in page.blocks:
            if block.kind == "image":
                path = image_path(self.path, block.image_path)
                width, height = fit_image(path)
                self.document.add_picture(str(path), width=Pt(width), height=Pt(height))
            elif block.kind == "table" and block.rows and any(block.rows):
                self._table(block.rows)
            else:
                for kind, text, level in text_parts(block.text):
                    paragraph = self.document.add_paragraph(style=f"Heading {min(level, 3)}" if kind == "heading" else None)
                    self._fill(paragraph, text, kind == "code")

    def _table(self, rows):
        widths = column_widths(rows)
        table = self.document.add_table(rows=0, cols=len(widths))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        borders = OxmlElement("w:tblBorders")
        for side in ["top", "left", "bottom", "right", "insideH", "insideV"]:
            element = OxmlElement(f"w:{side}")
            for name, value in [("val", "single"), ("sz", "4"), ("color", "D9D9D9")]:
                element.set(qn(f"w:{name}"), value)
            borders.append(element)
        table._tbl.tblPr.append(borders)
        for column, width in zip(table.columns, widths):
            column.width = Pt(width)
        for index, values in enumerate(rows):
            row = table.add_row()
            if index == 0:
                header = OxmlElement("w:tblHeader")
                row._tr.get_or_add_trPr().append(header)
            for col, cell in enumerate(row.cells):
                cell.width = Pt(widths[col])
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                paragraph = cell.paragraphs[0]
                paragraph.paragraph_format.space_before = Pt(5)
                paragraph.paragraph_format.space_after = Pt(5)
                self._fill(paragraph, str(values[col]) if col < len(values) else "")
                if index == 0:
                    shading = OxmlElement("w:shd")
                    shading.set(qn("w:fill"), "E9EEF3")
                    cell._tc.get_or_add_tcPr().append(shading)
        spacer = self.document.add_paragraph()
        spacer.paragraph_format.space_before = Pt(0)
        spacer.paragraph_format.space_after = Pt(4)
        spacer.paragraph_format.line_spacing = Pt(1)
        spacer.add_run().font.size = Pt(1)

    def finish(self):
        if not self.page_count:
            raise ValueError("没有可输出的页面")
        temporary = self.path.with_suffix(".partial.docx")
        try:
            self.document.save(temporary)
            temporary.replace(self.path)
        finally:
            temporary.unlink(missing_ok=True)
        return self.path
