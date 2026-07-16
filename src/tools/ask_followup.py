"""
src/tools/ask_followup.py
─────────────────────────────
Human-in-the-loop tool using LangGraph's interrupt mechanism.
The src calls this when it needs clarification before proceeding.
Execution pauses until a human responds via the API.
"""
from __future__ import annotations

from langchain_core.tools import tool
from langgraph.types import interrupt


@tool
def ask_followup(question: str) -> str:
    """
    Ask the user a clarifying question and pause execution until they respond.
    Use this when the user's intent is ambiguous or when you need
    additional information before taking an action.

    Args:
        question: The specific question to ask the user.
    """
    # LangGraph interrupt() suspends the graph and surfaces
    # `question` to the client. The resumed graph receives the
    # human's answer as the return value of interrupt().
    human_response: str = interrupt({"question": question})
    return human_response
