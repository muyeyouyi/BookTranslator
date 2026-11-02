"""书籍翻译器命令行入口。"""
from pathlib import Path

from loguru import logger

from book_translator.config import ConfigLoader
from book_translator.logging_setup import setup_logging
from book_translator.pipeline import BookTranslator
from book_translator.translation import TranslationError
from utils.argument_utils import build_parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    log_dir = Path(args.log_dir or "log").expanduser().resolve()
    setup_logging(log_dir)
    try:
        config = ConfigLoader().load(args)
        if config.log_dir != log_dir:
            setup_logging(config.log_dir)
        logger.info("加载配置完成：{}", config.config_path)
        output = BookTranslator(config).run()
        logger.success("输出文件：{}", output)
        return 0
    except KeyboardInterrupt:
        logger.warning("用户中断；已保存的翻译将在下次运行时复用")
        return 130
    except Exception as exc:
        # 不记录第三方异常正文、响应或 traceback，避免密钥和原文泄漏。
        if isinstance(exc, (ValueError, FileNotFoundError, TranslationError)):
            logger.error("{}", str(exc))
        else:
            logger.error("运行失败（{}）；请检查输入文件、接口配置和网络后重试", type(exc).__name__)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
