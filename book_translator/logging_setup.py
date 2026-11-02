import sys
from pathlib import Path

from loguru import logger


def setup_logging(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    logger.remove()
    fmt = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
    logger.add(sys.stderr, level="INFO", format=fmt, diagnose=False, backtrace=False)
    logger.add(directory / "translator.log", level="INFO", format=fmt,
               encoding="utf-8", rotation="10 MB", retention="7 days",
               diagnose=False, backtrace=False)
