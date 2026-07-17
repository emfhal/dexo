"""
src/tools/read_skill.py
──────────────────────────
Tool for the src to read its own skill files at runtime.
Useful for self-inspection and composing skill-based responses.
"""

from __future__ import annotations

from langchain_core.tools import tool

from src.config import get_settings
from src.context.sources.skills import load_skills


@tool
def read_skill(skill_name: str) -> str:
    """
    Read the full instructions of a skill by name.

    Args:
        skill_name: The exact name of the skill as declared in its SKILL.md frontmatter.
    """
    cfg = get_settings().assets
    skills = load_skills(cfg.skills_dir)

    for skill in skills:
        if skill["name"].lower() == skill_name.lower():
            return f"# Skill: {skill['name']}\n\n{skill['body']}"

    available = [s["name"] for s in skills]
    return f"⛔ Skill '{skill_name}' not found. Available skills: {', '.join(available) or 'none'}"
