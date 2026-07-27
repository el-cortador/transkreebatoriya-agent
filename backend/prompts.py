"""
Загрузчик core-промптов.

Промпты живут в core/prompts/*.md с YAML frontmatter (name, version) —
это переносимая, версионируемая часть ядра агента, а не строки в коде.
Тело промпта — всё после закрывающего `---` frontmatter.
"""

import re
from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "core" / "prompts"

_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", flags=re.DOTALL)


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    """
    Загружает промпт core/prompts/<name>.md без frontmatter.

    Raises:
        FileNotFoundError: Если файл промпта отсутствует.
    """
    path = PROMPTS_DIR / f"{name}.md"
    if not path.is_file():
        raise FileNotFoundError(f"Core-промпт не найден: {path}")

    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    body = text[match.end():] if match else text
    return body.strip()


def get_postprocess_system_prompt() -> str:
    """Системный промпт стадии постобработки (кэшируется после первого чтения)."""
    return load_prompt("postprocess.system")
