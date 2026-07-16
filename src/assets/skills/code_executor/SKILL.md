---
name: code_executor
description: >
  Writes, reviews, debugs, and runs code. Supports Python, JavaScript,
  shell scripts, and SQL. Uses the run_command tool with approval gating.
  Activate when the user asks to write, fix, or execute code.
---

# Code Executor Skill

## Supported languages
- Python (via `uv run python` or `python`)
- JavaScript / TypeScript (via `node` or `npx`)
- Shell (bash / zsh) — allowlisted commands only
- SQL (via `psql` or direct DB connection)

## Workflow
1. **Understand** the requirement — ask clarifying questions if ambiguous
2. **Write** the code with clear comments
3. **Request approval** before executing (use `run_command` — it gates on RBAC + human approval)
4. **Show output** and interpret results
5. **Iterate** if the output is unexpected

## Code quality standards
- Always use type hints in Python
- Prefer `pathlib.Path` over raw string paths
- Never hard-code secrets — use environment variables
- Add a `# Safety: ...` comment explaining any destructive operation

## Limitations
- Only commands in `COMMAND_ALLOWLIST` can run without special permission
- No network access from inside scripts unless via the `fetch_website` tool
