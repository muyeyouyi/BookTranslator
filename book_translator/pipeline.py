import hashlib
import time
from itertools import islice
from dataclasses import replace

from loguru import logger

from book_translator.checkpoint import CheckpointStore
from book_translator.output import create_writer
from book_translator.pdf_reader import PDFReader
from book_translator.translation import SYSTEM_PROMPT, TranslationService
from book_translator.table_translation import TableTranslationService


class BookTranslator:
    def __init__(self, config):
        self.config = config

    def run(self):
        config = self.config
        started = time.monotonic()
        config.output_dir.mkdir(parents=True, exist_ok=True)
        with config.input_path.open("rb") as stream:
            fingerprint = hashlib.file_digest(stream, "sha256").hexdigest()
        end = config.end_page or "end"
        page_suffix = f"_p{config.start_page}-{end}" if config.start_page != 1 or config.end_page is not None else ""
        stem = config.input_path.stem + page_suffix
        extension = {"markdown": "md", "pdf": "pdf", "docx": "docx"}[config.output_format]
        output = config.output_dir / f"{stem}.{'extracted' if config.extract_only else 'zh'}.{extension}"
        assets = config.output_dir / f"{stem}_{fingerprint[:12]}_assets"
        logger.info("开始{}：输入 {}，模型 {}", "本地提取" if config.extract_only else "翻译", config.input_path, config.model)
        # 先检查导出依赖与字体，避免翻译完成后才发现无法输出。
        writer = create_writer(config, output, config.input_path.stem)
        service = None
        if not config.extract_only:
            checkpoint = CheckpointStore(config.output_dir / ".checkpoints", {
                "file": fingerprint, "model": config.model, "base_url": config.base_url,
                "prompt": SYSTEM_PROMPT, "chunk_size": config.chunk_size,
                "max_output_tokens": config.max_output_tokens,
            }, config.resume)
            service = TranslationService(config, checkpoint)
        pages = PDFReader().read(config.input_path, assets, config.start_page, config.end_page)
        count = 0
        try:
            while batch := list(islice(pages, config.concurrency)):
                # 小窗口跨页调度，单页只有一个分段的书籍也可以并发。
                for page in self._translate_pages(batch, service):
                    writer.add_page(page)
                    count += 1
                    logger.info("第 {} 页已准备输出，格式 {}", page.number, config.output_format)
            result = writer.finish()
            logger.info("处理完成：{} 页，耗时 {:.1f} 秒", count, time.monotonic() - started)
            return result
        finally:
            pages.close()
            if service:
                service.close()

    def _translate_pages(self, pages, service):
        texts = []
        for page in pages:
            for block in page.blocks:
                if block.kind == "text":
                    texts.append(block.text)
        translated = dict(zip(texts, service.translate_many(texts))) if service else {}
        table_service = TableTranslationService(service) if service else None
        for page in pages:
            blocks = []
            for block in page.blocks:
                if block.kind == "image":
                    blocks.append(block)
                elif block.kind == "table":
                    rows = table_service.translate(block.rows) if table_service else block.rows
                    blocks.append(replace(block, rows=rows))
                else:
                    blocks.append(replace(block, text=translated.get(block.text, block.text)))
            yield replace(page, blocks=blocks)
