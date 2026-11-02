"""PDF 与 Word 共用的基础 Markdown 文本解析和版面尺寸。"""
import re
from urllib.parse import unquote

PAGE_WIDTH, PAGE_HEIGHT, MARGIN = 612, 792, 54  # Letter，单位 pt
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN
CONTENT_HEIGHT = PAGE_HEIGHT - 2 * MARGIN
SCAN_NOTICE = "本页没有可提取文字，已保留页面图片；未执行 OCR。"


def image_path(output_path, relative_path):
    return output_path.parent / unquote(relative_path)


def fit_image(path, max_width=CONTENT_WIDTH, max_height=CONTENT_HEIGHT - 70):
    from PIL import Image
    with Image.open(path) as image:
        width, height = image.size
    scale = min(max_width / width, max_height / height, 1)
    return width * scale, height * scale


def text_parts(text):
    """解析标题、段落、列表和代码；不执行 HTML 或远程资源。"""
    paragraph, code = [], None
    for line in text.splitlines() + [""]:
        if line.lstrip().startswith("```"):
            if paragraph:
                yield "paragraph", "\n".join(paragraph), 0
                paragraph = []
            if code is None:
                code = []
            else:
                yield "code", "\n".join(code), 0
                code = None
            continue
        if code is not None:
            code.append(line)
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        listed = re.match(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", line)
        if not line.strip() or heading or listed:
            if paragraph:
                yield "paragraph", "\n".join(paragraph), 0
                paragraph = []
            if heading:
                yield "heading", heading[2], len(heading[1])
            elif listed:
                yield "list", line.strip(), 0
        else:
            paragraph.append(line)
    if code:
        yield "code", "\n".join(code).rstrip("\n"), 0


def inline_spans(text):
    """返回 (文字, 强调类型)，支持粗体、斜体、行内代码和链接文字。"""
    pattern = r"\*\*(.+?)\*\*|`([^`]+)`|(?<!\*)\*([^*\n]+)\*(?!\*)|\[([^\]]+)\]\([^\s)]+\)"
    start = 0
    for match in re.finditer(pattern, text):
        if match.start() > start:
            yield text[start:match.start()], "normal"
        if match[1] is not None:
            yield match[1], "bold"
        elif match[2] is not None:
            yield match[2], "code"
        elif match[3] is not None:
            yield match[3], "italic"
        else:
            yield match[4], "normal"
        start = match.end()
    if start < len(text):
        yield text[start:], "normal"


def column_widths(rows, available=CONTENT_WIDTH):
    """根据内容长度分配宽度，限制单列权重，避免长段落挤垮其他列。"""
    count = max((len(row) for row in rows), default=0)
    weights = [max(4, min(24, max((len(str(row[i])) for row in rows if i < len(row)), default=4)))
               for i in range(count)]
    total = sum(weights)
    return [available * weight / total for weight in weights]
