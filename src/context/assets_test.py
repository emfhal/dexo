"""
src/context/assets_test.py
─────────────────────
Tests that verify the assets/ directory structure is valid:
- All SKILL.md files have required frontmatter
- All subagent manifests have required fields
- MCP servers config is valid JSON with required keys
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

ASSETS_ROOT = Path(__file__).parent.parent / "assets"
SKILLS_ROOT = ASSETS_ROOT / "skills"
SUBAGENTS_ROOT = ASSETS_ROOT / "subagents"
MCP_CONFIG = ASSETS_ROOT / "mcp" / "servers.json"
RULES_FILE = ASSETS_ROOT / "rules" / "AGENTS.md"


class TestSkillAssets:
    def test_skills_directory_exists(self) -> None:
        assert SKILLS_ROOT.is_dir(), f"Skills directory missing: {SKILLS_ROOT}"

    @pytest.mark.parametrize(
        "skill_dir", list(SKILLS_ROOT.iterdir()) if SKILLS_ROOT.exists() else []
    )
    def test_each_skill_has_skill_md(self, skill_dir: Path) -> None:
        if not skill_dir.is_dir():
            return
        skill_md = skill_dir / "SKILL.md"
        assert skill_md.exists(), f"Missing SKILL.md in {skill_dir}"

    @pytest.mark.parametrize(
        "skill_dir", list(SKILLS_ROOT.iterdir()) if SKILLS_ROOT.exists() else []
    )
    def test_skill_md_has_valid_frontmatter(self, skill_dir: Path) -> None:
        if not skill_dir.is_dir():
            return
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            return

        content = skill_md.read_text()
        assert content.startswith("---"), f"{skill_md}: must start with YAML frontmatter (---)"

        parts = content.split("---", 2)
        assert len(parts) >= 3, f"{skill_md}: frontmatter not properly closed"

        meta = yaml.safe_load(parts[1])
        assert "name" in meta, f"{skill_md}: frontmatter missing 'name'"
        assert "description" in meta, f"{skill_md}: frontmatter missing 'description'"
        assert len(meta["description"]) > 10, f"{skill_md}: description too short"


class TestSubagentAssets:
    def test_subagents_directory_exists(self) -> None:
        assert SUBAGENTS_ROOT.is_dir(), f"Subagents directory missing: {SUBAGENTS_ROOT}"

    @pytest.mark.parametrize(
        "subagent_dir",
        list(SUBAGENTS_ROOT.iterdir()) if SUBAGENTS_ROOT.exists() else [],
    )
    def test_each_subagent_has_manifest(self, subagent_dir: Path) -> None:
        if not subagent_dir.is_dir():
            return
        manifest = subagent_dir / "manifest.json"
        assert manifest.exists(), f"Missing manifest.json in {subagent_dir}"

    @pytest.mark.parametrize(
        "subagent_dir",
        list(SUBAGENTS_ROOT.iterdir()) if SUBAGENTS_ROOT.exists() else [],
    )
    def test_manifest_has_required_fields(self, subagent_dir: Path) -> None:
        if not subagent_dir.is_dir():
            return
        manifest_file = subagent_dir / "manifest.json"
        if not manifest_file.exists():
            return

        data = json.loads(manifest_file.read_text())
        assert "name" in data, f"{manifest_file}: missing 'name'"
        assert "description" in data, f"{manifest_file}: missing 'description'"
        assert "model" in data, f"{manifest_file}: missing 'model' config"
        assert "provider" in data["model"], f"{manifest_file}: model missing 'provider'"
        assert "model" in data["model"], f"{manifest_file}: model missing 'model'"

    @pytest.mark.parametrize(
        "subagent_dir",
        list(SUBAGENTS_ROOT.iterdir()) if SUBAGENTS_ROOT.exists() else [],
    )
    def test_manifest_provider_is_known(self, subagent_dir: Path) -> None:
        if not subagent_dir.is_dir():
            return
        manifest_file = subagent_dir / "manifest.json"
        if not manifest_file.exists():
            return

        data = json.loads(manifest_file.read_text())
        provider = data.get("model", {}).get("provider", "")
        valid_providers = {"openai", "anthropic", "gemini", "ollama"}
        assert provider in valid_providers, (
            f"{manifest_file}: unknown provider '{provider}'. Valid: {valid_providers}"
        )


class TestMCPConfig:
    def test_mcp_config_exists(self) -> None:
        assert MCP_CONFIG.exists(), f"MCP servers config missing: {MCP_CONFIG}"

    def test_mcp_config_is_valid_json(self) -> None:
        data = json.loads(MCP_CONFIG.read_text())
        assert isinstance(data, list), "MCP config must be a JSON array"

    def test_each_server_has_required_fields(self) -> None:
        servers = json.loads(MCP_CONFIG.read_text())
        for server in servers:
            assert "name" in server, f"MCP server missing 'name': {server}"
            assert "command" in server, f"MCP server missing 'command': {server}"


class TestRulesAssets:
    def test_agents_md_exists(self) -> None:
        assert RULES_FILE.exists(), f"AGENTS.md not found: {RULES_FILE}"

    def test_agents_md_not_empty(self) -> None:
        content = RULES_FILE.read_text()
        assert len(content) > 50, "AGENTS.md appears to be nearly empty"
