import argparse
from pathlib import Path


def build_parser():
    parser = argparse.ArgumentParser(description="本地读取 PDF，调用 LLM 翻译为中文，输出 Markdown、PDF 或 Word")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parents[1] / "config.yaml"), help="YAML 配置文件")
    parser.add_argument("--model", help="覆盖配置中的模型名称")
    parser.add_argument("--input", "--book", dest="input", help="输入 PDF 路径")
    parser.add_argument("--input-format", choices=["pdf"], help="输入格式，目前仅支持 pdf")
    parser.add_argument("--output-format", choices=["markdown", "md", "pdf", "word", "docx"], help="输出格式，默认读取配置；word/docx 均输出 .docx")
    parser.add_argument("--pdf-font", help="PDF 中文字体文件路径（TTF 或包含 TrueType 字形的 TTC），默认自动检测")
    parser.add_argument("--output-dir", help="输出目录")
    parser.add_argument("--log-dir", help="日志目录，默认 log/")
    parser.add_argument("--concurrency", type=int, help="模型请求并发数，默认 3；设为 1 串行处理")
    parser.add_argument("--start-page", type=int, help="起始页，从 1 开始")
    parser.add_argument("--end-page", type=int, help="结束页，包含该页")
    parser.add_argument("--extract-only", action="store_true", help="仅本地提取，不调用模型，用于预览文本、表格和图片")
    parser.add_argument("--no-resume", action="store_true", help="忽略已有翻译缓存，重新翻译")
    return parser
