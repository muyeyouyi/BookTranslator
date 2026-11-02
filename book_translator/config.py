import math
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class AppConfig:
    config_path: Path
    input_path: Path
    output_dir: Path
    log_dir: Path
    model: str
    api_key: str = field(repr=False)
    base_url: str | None = None
    chunk_size: int = 3000
    timeout: float = 120
    max_retries: int = 3
    max_output_tokens: int = 4096
    concurrency: int = 3
    output_format: str = "markdown"
    pdf_font: Path | None = None
    start_page: int = 1
    end_page: int | None = None
    extract_only: bool = False
    resume: bool = True


class ConfigLoader:
    """命令行逐项覆盖 YAML；兼容原有 QianwenModel/common 配置。"""

    def load(self, args):
        path = Path(args.config).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"配置文件不存在：{path}")
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            raise ValueError("YAML 配置语法错误，请检查缩进和字段格式") from None
        if not isinstance(data, dict):
            raise ValueError("配置文件顶层必须是映射")
        model = data.get("llm", data.get("QianwenModel", {}))
        common = data.get("common", {})
        if not isinstance(model, dict) or not isinstance(common, dict):
            raise ValueError("llm/QianwenModel 和 common 必须是映射")

        def choose(name, default=None):
            value = getattr(args, name, None)
            return value if value is not None else common.get(name, default)

        def resolve(value, cli=False):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("文件和目录路径必须为非空字符串")
            candidate = Path(value).expanduser()
            return (candidate if candidate.is_absolute() else (Path.cwd() if cli else path.parent) / candidate).resolve()

        input_value = args.input if args.input is not None else common.get("input", common.get("book"))
        input_path = resolve(input_value, args.input is not None)
        if not input_path.is_file():
            raise FileNotFoundError(f"输入文件不存在：{input_path}")
        if str(choose("input_format", "pdf")).lower() != "pdf":
            raise ValueError("目前仅支持 PDF 输入")
        output_format = choose("output_format", common.get("file_format", "markdown"))
        formats = {"md": "markdown", "markdown": "markdown", "pdf": "pdf", "word": "docx", "docx": "docx"}
        output_format = formats.get(str(output_format).lower())
        if output_format is None:
            raise ValueError("输出格式必须是 markdown/md、pdf 或 word/docx")
        font_value = choose("pdf_font")
        pdf_font = resolve(font_value, args.pdf_font is not None) if font_value is not None else None
        if output_format == "pdf" and pdf_font is not None and not pdf_font.is_file():
            raise FileNotFoundError(f"PDF 字体文件不存在：{pdf_font}")

        def number(name, default, integer=True, minimum=1):
            value = choose(name, default)
            if value is None and default is None:
                return None
            if isinstance(value, bool) or (integer and not isinstance(value, int)):
                raise ValueError(f"{name} 必须是整数")
            try:
                result = int(value) if integer else float(value)
            except (TypeError, ValueError, OverflowError):
                raise ValueError(f"{name} 必须是有效数字") from None
            if not math.isfinite(result) or result < minimum:
                raise ValueError(f"{name} 必须大于等于 {minimum}")
            return result

        model_name = args.model if args.model is not None else model.get("model", "")
        key_env = model.get("api_key_env", "OPENAI_API_KEY")
        if not isinstance(key_env, str):
            raise ValueError("api_key_env 必须是环境变量名称")
        api_key = os.environ.get(key_env) or model.get("api_key", "")
        base_url = model.get("base_url")
        if not isinstance(model_name, str) or not isinstance(api_key, str):
            raise ValueError("model 和 api_key 必须是字符串")
        if not args.extract_only and (not model_name.strip() or not api_key.strip()):
            raise ValueError("翻译需要配置模型名称和 API Key；也可通过环境变量提供密钥")
        if base_url is not None and (not isinstance(base_url, str) or not base_url.startswith(("https://", "http://"))):
            raise ValueError("base_url 必须是 HTTP/HTTPS 接口地址")
        start, end = number("start_page", 1), number("end_page", None)
        if end is not None and end < start:
            raise ValueError("end_page 不能小于 start_page")
        return AppConfig(
            config_path=path, input_path=input_path,
            output_dir=resolve(choose("output_dir", "output"), args.output_dir is not None),
            log_dir=resolve(choose("log_dir", "log"), args.log_dir is not None),
            model=model_name.strip(), api_key=api_key, base_url=base_url,
            chunk_size=number("chunk_size", 3000), timeout=number("timeout", 120, integer=False),
            max_retries=number("max_retries", 3, minimum=0),
            max_output_tokens=number("max_output_tokens", 4096),
            concurrency=number("concurrency", 3),
            output_format=output_format, pdf_font=pdf_font,
            start_page=start, end_page=end, extract_only=args.extract_only,
            resume=not args.no_resume,
        )
