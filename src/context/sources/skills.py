"""
src/context/sources/skills.py
─────────────────────────────────
Discovers and loads SKILL.md files from a configured skills directory.
Parses YAML frontmatter for name/description, and returns the full body.
Only skills whose description matches the current query are injected.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TypedDict

import yaml

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)


class SkillEntry(TypedDict):
    name: str
    description: str
    body: str
    path: str


def load_skills(skills_dir: str) -> list[SkillEntry]:
    """
    Recursively discover all SKILL.md files in `skills_dir`.
    Parses YAML frontmatter for name + description.
    Returns a list of SkillEntry dicts.
    """
    root = Path(skills_dir)
    if not root.exists():
        logger.warning("Skills directory not found: %s", skills_dir)
        return []

    entries: list[SkillEntry] = []
    for skill_md in root.rglob("SKILL.md"):
        try:
            content = skill_md.read_text(encoding="utf-8")
            m = _FRONTMATTER_RE.match(content)
            if not m:
                logger.warning("No YAML frontmatter in %s — skipping.", skill_md)
                continue
            meta = yaml.safe_load(m.group(1)) or {}
            body = m.group(2).strip()
            entries.append(
                SkillEntry(
                    name=meta.get("name", skill_md.parent.name),
                    description=meta.get("description", ""),
                    body=body,
                    path=str(skill_md),
                )
            )
        except Exception as exc:
            logger.error("Failed to load skill %s: %s", skill_md, exc)

    logger.debug("Loaded %d skills from %s", len(entries), skills_dir)
    return entries
