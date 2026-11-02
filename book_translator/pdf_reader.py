from pathlib import Path
from urllib.parse import quote

import pdfplumber
from loguru import logger

from book_translator.models import ContentBlock, PageContent


def _inside(obj, box):
    """按字符中心归属区域，避免移除表格外的相邻文字。"""
    x, y = (obj["x0"] + obj["x1"]) / 2, (obj["top"] + obj["bottom"]) / 2
    return box[0] <= x <= box[2] and box[1] <= y <= box[3]


class PDFReader:
    """本地提取文字和表格，图片按原区域渲染为 PNG，不请求云端。"""

    def read(self, path: Path, assets_dir: Path, start=1, end=None):
        assets_dir.mkdir(parents=True, exist_ok=True)
        with pdfplumber.open(path) as pdf:
            total = len(pdf.pages)
            end = total if end is None else end
            if start > total or end > total:
                raise ValueError(f"页码超出范围，PDF 共 {total} 页")
            logger.info("PDF 共 {} 页，本次处理 {}-{} 页", total, start, end)
            for index in range(start - 1, end):
                page = pdf.pages[index]
                try:
                    blocks = self._extract_page(page, assets_dir, index + 1)
                    has_text = bool(page.chars)
                    if not has_text:
                        logger.warning("第 {} 页没有可提取文字；保留图像内容，不执行 OCR", index + 1)
                    logger.info("第 {} 页提取完成：{} 个内容块", index + 1, len(blocks))
                    yield PageContent(index + 1, blocks, has_text)
                finally:
                    page.close()

    def _extract_page(self, page, assets_dir, number):
        elements = []
        tables = page.find_tables()
        boxes = [t.bbox for t in tables]
        for table in tables:
            rows = [[str(cell or "").strip() for cell in row] for row in table.extract()]
            if rows and any(any(row) for row in rows):
                elements.append((table.bbox[1], table.bbox[0], ContentBlock("table", rows=rows)))

        # 不把表格单元格再次混入正文。
        prose = page.filter(lambda obj: obj.get("object_type") != "char" or not any(_inside(obj, b) for b in boxes))
        lines = prose.extract_text_lines(layout=False, strip=True, return_chars=True)
        paragraph, last_bottom, last_size = [], None, None
        separators = boxes + [(i["x0"], i["top"], i["x1"], i["bottom"]) for i in page.images]

        def flush():
            if paragraph:
                elements.append((paragraph[0]["top"], paragraph[0]["x0"],
                                 ContentBlock("text", text="\n".join(line["text"] for line in paragraph))))
                paragraph.clear()

        for line in lines:
            chars = line.get("chars", [])
            size = max((c.get("size", 10) for c in chars), default=10)
            crossed_element = last_bottom is not None and any(last_bottom <= box[1] < line["top"] for box in separators)
            if paragraph and (line["top"] - last_bottom > max(5, size * 0.7)
                              or abs(size - last_size) > 2 or crossed_element):
                flush()
            paragraph.append(line)
            last_bottom, last_size = line["bottom"], size
        flush()

        # 没有文字不等于整页扫描图；优先提取实际图片区域。
        seen = set()
        for image in page.images:
            box = (max(page.bbox[0], image["x0"]), max(page.bbox[1], image["top"]),
                   min(page.bbox[2], image["x1"]), min(page.bbox[3], image["bottom"]))
            if box in seen or box[2] <= box[0] or box[3] <= box[1]:
                continue
            seen.add(box)
            name = f"page_{number:04d}_image_{len(seen):03d}.png"
            page.crop(box).to_image(resolution=150).original.save(assets_dir / name)
            elements.append((box[1], box[0], self._image_block(assets_dir, name)))
        if not page.chars and not seen:
            # 例如只有矢量图的页面，无法获取独立图片时才保留整页预览。
            name = f"page_{number:04d}.png"
            page.to_image(resolution=150).original.save(assets_dir / name)
            elements.append((0, 0, self._image_block(assets_dir, name)))
            logger.info("第 {} 页没有可导出的图片对象，使用整页预览", number)
        return [item[2] for item in sorted(elements, key=lambda item: (item[0], item[1]))]

    @staticmethod
    def _image_block(assets_dir, name):
        return ContentBlock("image", image_path=quote(f"{assets_dir.name}/{name}", safe="/"))
