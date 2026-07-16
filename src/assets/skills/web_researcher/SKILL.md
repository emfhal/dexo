---
name: web_researcher
description: >
  Searches the web, fetches URLs, reads documentation, and synthesises
  findings into clear summaries with citations. Activate when the user
  asks to research a topic, find documentation, or look up current information.
---

# Web Researcher Skill

## When to use this skill
- User asks to search for something online
- User wants documentation from an external source
- User needs up-to-date information you don't have in context

## Workflow
1. **Decompose** the query into specific search sub-questions
2. **Fetch** the most relevant URLs (use `fetch_website` tool)
3. **Synthesise** findings into a concise, cited response
4. **Verify** — if sources conflict, note the discrepancy

## Output format
Always end with a `## Sources` section listing every URL you fetched.

## Safety rules
- Never fetch URLs from the SSRF blocklist
- Truncate page content longer than 4,000 tokens before injecting into context
- Do not store fetched PII in memory backends
