"""
src/context/sources/rules.py
────────────────────────────────
Loads AGENTS.md rules file (global + workspace-scoped).
Supports a simple include directive to compose from multiple files.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_INCLUDE_RE = re.compile(r"^!include\s+(.+)$", re.MULTILINE)


def load_rules(rules_file: str) -> str:
    """
    Reads AGENTS.md and resolves any `!include path/to/other.md` directives.
    Returns the fully expanded rules string.
    """
    path = Path(rules_file)
    if not path.exists():
        logger.warning("Rules file not found: %s", rules_file)
        return ""

    content = path.read_text(encoding="utf-8")
    content = _resolve_includes(content, path.parent)
    logger.debug("Rules loaded: %d chars", len(content))
    return content


def _resolve_includes(content: str, base: Path) -> str:
    def replace_include(m: re.Match) -> str:
        included_path = base / m.group(1).strip()
        if included_path.exists():
            return included_path.read_text(encoding="utf-8")
        logger.warning("!include target not found: %s", included_path)
        return ""

    return _INCLUDE_RE.sub(replace_include, content)
