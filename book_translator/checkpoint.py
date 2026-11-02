import hashlib
import json
from pathlib import Path
from threading import Lock

from loguru import logger


def atomic_write(path: Path, text: str):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


class CheckpointStore:
    """逐段持久化；文件、模型或提示词变化后不会误命中旧译文。"""

    def __init__(self, directory: Path, identity: dict, resume=True):
        digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / f"{digest}.json"
        self.values = {}
        self._lock = Lock()
        if resume and self.path.exists():
            try:
                values = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(values, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in values.items()):
                    raise ValueError
                self.values = values
                logger.info("已加载 {} 条翻译缓存", len(values))
            except (ValueError, UnicodeError):
                logger.warning("翻译缓存损坏，将重新翻译")

    @staticmethod
    def key(text):
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get(self, text):
        with self._lock:
            return self.values.get(self.key(text))

    def put(self, text, translated):
        with self._lock:
            self.values[self.key(text)] = translated
            atomic_write(self.path, json.dumps(self.values, ensure_ascii=False, indent=2))
