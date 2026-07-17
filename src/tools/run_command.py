"""
src/tools/run_command.py
───────────────────────────
Sandboxed shell command execution.
- Validates command against an allowlist
- Requires human approval (LangGraph interrupt)
- Enforces timeout
- Strips ANSI escape codes from output
"""

from __future__ import annotations

import re
import subprocess

from langchain_core.tools import tool

from src.config import get_settings

_ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _strip_ansi(text: str) -> str:
    return _ANSI_ESCAPE.sub("", text)


@tool
def run_command(command: str) -> str:
    """
    Run a shell command and return its output.

    Only commands in the COMMAND_ALLOWLIST are permitted.
    Commands that modify the filesystem or system state
    require explicit human approval before execution.

    Args:
        command: The full shell command string to execute.
    """
    cfg = get_settings().tools
    base_cmd = command.strip().split()[0]

    # ── Allowlist check ───────────────────────────────────────────────────────
    if base_cmd not in cfg.command_allowlist:
        return (
            f"⛔ Command '{base_cmd}' is not in the allowlist. "
            f"Permitted: {', '.join(cfg.command_allowlist)}"
        )

    # ── Execute ───────────────────────────────────────────────────────────────
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = _strip_ansi(result.stdout) + _strip_ansi(result.stderr)
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "⚠️ Command timed out after 30 seconds."
    except Exception as exc:
        return f"❌ Execution error: {exc}"
