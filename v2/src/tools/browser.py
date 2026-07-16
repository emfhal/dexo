"""
src/tools/browser.py
───────────────────────
Chromium browser tool using Playwright for complex, multi-step actions.
Supports navigating, clicking, filling forms, and reading text.
Requires human approval since browser actions can be destructive.
"""
from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool
from playwright.async_api import async_playwright

from src.config import get_settings


@tool
async def browser_action(actions_json: str) -> str:
    """
    Execute a sequence of multi-step actions in a Chromium browser.
    Use this to interact with dynamic web apps, fill forms, and click buttons.

    Args:
        actions_json: A JSON string containing a list of action objects.
          Each object must have an 'action' key.
          Supported actions:
            - {"action": "goto", "url": "https://..."}
            - {"action": "click", "selector": "css_selector"}
            - {"action": "fill", "selector": "css_selector", "value": "text to type"}
            - {"action": "wait", "timeout": milliseconds}
            - {"action": "extract_text", "selector": "body"}
          
          Example:
          [
            {"action": "goto", "url": "https://example.com/login"},
            {"action": "fill", "selector": "#username", "value": "myuser"},
            {"action": "fill", "selector": "#password", "value": "secret"},
            {"action": "click", "selector": "button[type='submit']"},
            {"action": "wait", "timeout": 2000},
            {"action": "extract_text", "selector": ".dashboard-welcome"}
          ]
    """
    try:
        actions = json.loads(actions_json)
        if not isinstance(actions, list):
            return "❌ Error: actions_json must be a JSON array of objects."
    except json.JSONDecodeError as exc:
        return f"❌ JSON Decode Error: {exc}"

    cfg = get_settings().tools
    extracted_data: list[str] = []
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="LangGraph-Agent/2.0 (research browser tool)",
                record_video_dir="records/"
            )
            page = await context.new_page()

            # Execute actions sequentially
            for step in actions:
                action_type = step.get("action")
                
                try:
                    if action_type == "goto":
                        url = step.get("url")
                        if not url:
                            raise ValueError("Missing 'url' for goto action.")
                        # Basic SSRF protection by forcing http/https
                        if not url.startswith(("http://", "https://")):
                            raise ValueError("Only http/https URLs are permitted.")
                        await page.goto(url, timeout=cfg.fetch_timeout_seconds * 1000)
                    
                    elif action_type == "click":
                        selector = step.get("selector")
                        if not selector:
                            raise ValueError("Missing 'selector' for click action.")
                        await page.click(selector, timeout=cfg.fetch_timeout_seconds * 1000)
                    
                    elif action_type == "fill":
                        selector = step.get("selector")
                        value = step.get("value", "")
                        if not selector:
                            raise ValueError("Missing 'selector' for fill action.")
                        await page.fill(selector, value, timeout=cfg.fetch_timeout_seconds * 1000)
                    
                    elif action_type == "wait":
                        timeout = step.get("timeout", 1000)
                        await page.wait_for_timeout(timeout)
                        
                    elif action_type == "extract_text":
                        selector = step.get("selector", "body")
                        element = await page.query_selector(selector)
                        if element:
                            text = await element.inner_text()
                            extracted_data.append(f"Text from '{selector}':\n{text[:8000]}")
                        else:
                            extracted_data.append(f"Text from '{selector}': Element not found.")
                    
                    else:
                        return f"❌ Unknown action type: '{action_type}'"
                        
                except Exception as step_exc:
                    await browser.close()
                    return f"❌ Error executing step {step}: {step_exc}"

            await browser.close()
            
            if extracted_data:
                return "\n\n---\n\n".join(extracted_data)
            return "✅ All browser actions executed successfully. (No text was extracted)"

    except Exception as exc:
        return f"❌ Browser error: {exc}"
