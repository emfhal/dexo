"""
src/context/sources/system_prompt.py
────────────────────────────────────────
Jinja2-based system prompt builder.
Renders a base template, injecting runtime context (user, permissions, date).
"""
from __future__ import annotations

from datetime import UTC, datetime

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

_env = Environment(
    loader=PackageLoader("src", "templates"),
    autoescape=select_autoescape(enabled_extensions=("html",)),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_system_prompt(
    user_id: str,
    roles: list[str],
    extra: dict | None = None,
) -> str:
    """
    Renders the system prompt template with runtime values.
    Template is at src/templates/system_prompt.j2
    """
    template = _env.get_template("system_prompt.j2")
    return template.render(
        user_id=user_id,
        roles=roles,
        now_utc=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        **(extra or {}),
    )
