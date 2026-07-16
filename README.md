# Dexo - Multi-Agent Orchestration Architecture

This repository contains a state-of-the-art multi-agent development environment leveraging Vercel Services to run Fastify and FastAPI orchestrators in parallel.

## Deployment

Deploy this full stack multi-agent architecture with a single click using Vercel. This will deploy the Fastify (Node.js) agents, the FastAPI (Python) agents, and configure the internal bindings automatically.

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/your-username/your-agent-repo&env=OPENAI_API_KEY,ANTHROPIC_API_KEY,DATABASE_URL)

## Architecture

* **orchestrators/vercel_ai_agent**: Fastify + Vercel AI SDK
* **orchestrators/genkit_agent**: Fastify + Google Genkit SDK
* **subagents/langchain_js_agent**: Fastify + LangChain.js
* **orchestrators/langchain_agent**: FastAPI + LangChain
* **orchestrators/crewai_agent**: FastAPI + CrewAI
* **mcp/local_server**: Fastify MCP Server

## Development

Run locally using Vercel CLI:
```bash
vercel dev
```
