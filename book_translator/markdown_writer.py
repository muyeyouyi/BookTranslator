from pathlib import Path

from book_translator.checkpoint import atomic_write


def table_to_markdown(rows):
    if not rows:
        return ""
    width = max(map(len, rows))
    if not width:
        return ""

    def cell(value):
        return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")

    normalized = [list(row) + [""] * (width - len(row)) for row in rows]
    lines = ["| " + " | ".join(cell(value) for value in row) + " |" for row in normalized]
    lines.insert(1, "| " + " | ".join(["---"] * width) + " |")
    return "\n".join(lines)


class MarkdownWriter:
    def __init__(self, output_path: Path, title: str, extract_only=False):
        self.path = output_path
        self.partial_path = output_path.with_suffix(".partial.md")
        self.header = f"# {title}\n\n" + ("<!-- 本地提取预览，尚未翻译 -->\n" if extract_only else "")
        self.started = False

    def add_page(self, page):
        rendered = []
        for block in page.blocks:
            if block.kind == "image":
                rendered.append(f"![原 PDF 第 {page.number} 页图片]({block.image_path})")
            elif block.kind == "table":
                rendered.append(table_to_markdown(block.rows))
            else:
                rendered.append(block.text)
        content = "\n\n".join(rendered)
        notice = "\n> 本页没有可提取文字，已保留图像内容；未执行 OCR。\n" if not page.has_text else ""
        section = f"\n<!-- 原 PDF 第 {page.number} 页 -->\n{notice}\n{content}\n"
        if not self.started:
            atomic_write(self.partial_path, self.header + section)
            self.started = True
        else:
            # 逐页追加，长书不需要反复重写或在内存中保留全部译文。
            with self.partial_path.open("a", encoding="utf-8") as stream:
                stream.write(section)

    def finish(self):
        if not self.started:
            raise ValueError("没有可输出的页面")
        self.partial_path.replace(self.path)
        return self.path
