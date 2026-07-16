import os
import json
from typing import List, Dict, Any
from langchain_core.tools import tool

class CustomizationsLoader:
    """
    Loads custom skills, rules, and subagents from a local .agents folder or an MCP server.
    """
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.agents_dir = os.path.join(workspace_root, ".agents")
        
    def load_rules(self) -> str:
        """Reads AGENTS.md to inject system prompt constraints."""
        rules_path = os.path.join(self.agents_dir, "AGENTS.md")
        if os.path.exists(rules_path):
            with open(rules_path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""

    def load_local_skills(self) -> List[Any]:
        """
        Scans .agents/skills/ for SKILL.md files and wraps them into LangChain tools.
        """
        skills_dir = os.path.join(self.agents_dir, "skills")
        dynamic_tools = []
        
        if not os.path.exists(skills_dir):
            return dynamic_tools
            
        for item in os.listdir(skills_dir):
            skill_path = os.path.join(skills_dir, item)
            if os.path.isdir(skill_path):
                skill_md = os.path.join(skill_path, "SKILL.md")
                if os.path.exists(skill_md):
                    # In a full implementation, we parse the YAML frontmatter for name/description
                    # and construct a dynamic LangChain @tool that executes the skill logic.
                    # Mocking the dynamic tool creation:
                    
                    def make_skill_tool(name: str):
                        @tool(name=f"skill_{name}")
                        def dynamic_skill_runner(input_str: str) -> str:
                            f"Executes the {name} skill based on SKILL.md instructions."
                            return f"Executed skill {name} with input {input_str}"
                        return dynamic_skill_runner
                        
                    dynamic_tools.append(make_skill_tool(item))
                    
        return dynamic_tools

    def load_mcp_tools(self) -> List[Any]:
        """
        Connects to standard MCP servers to load external tools.
        """
        # E.g., load tools from 'mcp_server' Node.js app or Zep MCP.
        # This requires using an MCP client (like @modelcontextprotocol/sdk equivalent in Python)
        return []

    def get_available_subagents(self) -> List[str]:
        """
        Parses subagents configuration from .agents/subagents.json or similar.
        """
        config_path = os.path.join(self.agents_dir, "subagents.json")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                data = json.load(f)
                return [s.get("name") for s in data.get("subagents", [])]
        return ["coder-node", "planner-py", "researcher-py"]
