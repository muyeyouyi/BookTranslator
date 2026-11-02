from book_translator.markdown_writer import MarkdownWriter


def create_writer(config, path, title):
    """按需加载输出库，Markdown 用户不需要安装 Word 依赖。"""
    if config.output_format == "markdown":
        return MarkdownWriter(path, title, config.extract_only)
    if config.output_format == "pdf":
        from book_translator.pdf_writer import PDFWriter
        return PDFWriter(path, title, config.extract_only, config.pdf_font)
    if config.output_format == "docx":
        try:
            from book_translator.word_writer import WordWriter
        except ImportError:
            raise ValueError("Word 输出需要 python-docx，请在当前环境执行 python -m pip install -r requirements.txt") from None
        return WordWriter(path, title, config.extract_only)
    raise ValueError("不支持的输出格式")
