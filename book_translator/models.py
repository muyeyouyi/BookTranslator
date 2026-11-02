from dataclasses import dataclass


@dataclass
class ContentBlock:
    kind: str  # text / table / image
    text: str = ""
    rows: list[list[str]] | None = None
    image_path: str | None = None


@dataclass
class PageContent:
    number: int
    blocks: list[ContentBlock]
    has_text: bool
