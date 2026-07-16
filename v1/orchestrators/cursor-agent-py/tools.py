import os
import subprocess
from typing import List, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from bs4 import BeautifulSoup
import urllib.request
import urllib.error

@tool
def read_skill(file_paths: List[str]) -> str:
    """
    Safely reads the contents of the specified files.
    This tool is used to pull codebase context into awareness.
    Returns the file contents separated by '---' delimiters.
    """
    # Define workspace boundary to prevent directory traversal
    workspace_root = os.path.abspath(os.getcwd())
    
    output = []
    for path in file_paths:
        abs_path = os.path.abspath(path)
        if not abs_path.startswith(workspace_root):
            output.append(f"Error: Access denied for {path}. Outside workspace boundary.")
            continue
            
        if not os.path.isfile(abs_path):
            output.append(f"Error: File not found {path}.")
            continue
            
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
                output.append(f"File: {abs_path}\n{content}")
        except Exception as e:
            output.append(f"Error reading {path}: {str(e)}")
            
    return "\n---\n".join(output)

@tool
def run_command(command: str, timeout_seconds: int = 30) -> str:
    """
    Executes a shell command within the isolated environment.
    Use this to run test suites, execute linters, or compile code.
    Captures stdout and stderr and enforces a strict timeout.
    """
    try:
        # Note: In a production environment, this should run inside a devcontainer or VM.
        # Here we use subprocess with strict timeouts for containment.
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=os.getcwd()
        )
        output = f"Exit Code: {result.returncode}\n"
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        return output
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout_seconds} seconds."
    except Exception as e:
        return f"Error executing command: {str(e)}"

@tool
def fetch_website(url: str) -> str:
    """
    Fetches a given URL and extracts its content as clean Markdown.
    Use this to research external documentation missing from training data.
    """
    try:
        req = urllib.request.Request(
            url, 
            data=None, 
            headers={'User-Agent': 'Mozilla/5.0 Cursor-Like-Agent'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read()
            
        # Parse HTML and strip boilerplate
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.extract()
            
        text = soup.get_text(separator='\n', strip=True)
        return text
    except Exception as e:
        return f"Error fetching website {url}: {str(e)}"

@tool
def follow_questions(question: str, options: Optional[List[str]] = None) -> str:
    """
    A circuit breaker tool. Use this when the user query is critically ambiguous
    and you need deterministic clarification before proceeding.
    Halts execution to ask the user.
    """
    # In LangGraph, returning a specific artifact or raising a specific exception
    # can trigger a human-in-the-loop interruption.
    # For this implementation, we return a structured request that the orchestrator
    # will intercept to pause execution.
    prompt = f"CLARIFICATION REQUIRED: {question}"
    if options:
        prompt += f"\nOptions: {', '.join(options)}"
    
    # We prefix with a special token that the src loop can intercept
    return f"__INTERRUPT__: {prompt}"

@tool
def invoke_subagent(subagent_name: str, instruction: str) -> str:
    """
    Delegates a task to a specialized subagent (e.g., 'researcher', 'coder').
    """
    # Mock implementation of subagent delegation.
    # In a full implementation, this would trigger an external API call or another LangGraph.
    return f"__DELEGATE__:{subagent_name}:{instruction}"
