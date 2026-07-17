# Dexo - Enterprise Agentic Orchestrator

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/logo.svg">
    <source media="(prefers-color-scheme: light)" srcset="./assets/logo-black.svg">
    <img alt="Dexo Logo" src="./assets/logo.svg" width="200">
  </picture>
</div>

A robust, frontier-grade multi-agent architecture powered by LangGraph, FastAPI, and OpenTelemetry. Designed for high scalability, observability, and modular tool integration. The codebase follows standard Python packaging (`src/` layout) and is deployment-ready for Vercel Serverless Functions.

## 🚀 Why Dexo?

Many people build "toy" AI agents that only work locally in a Jupyter notebook, but Dexo is engineered as a deeply robust, deployable microservices architecture. Here is a breakdown of why this is a frontier-grade, production-ready AI platform:

### 1. Enterprise Architecture & Speed
- **uv Native**: By managing the Python ecosystem entirely with uv, dependency resolution, locking, and syncing are blazingly fast and perfectly reproducible.
- **FastAPI + Serverless Ready**: The core orchestrator is exposed via a high-performance ASGI FastAPI server that supports Server-Sent Events (SSE) for token streaming. It's built exactly how Vercel or AWS Lambda expects modern Python microservices to look.

### 2. Multi-Provider & Hybrid Memory
- **Model Agnostic**: Instead of locking into one ecosystem, Dexo gracefully supports OpenAI, Anthropic, Google Gemini, and even local fallback models via Ollama.
- **Long-term Semantic Memory**: By integrating Zep, Mem0, and Postgres with pgvector, Dexo has the ability to maintain state, remember past conversations, and perform semantic vector searches natively.

### 3. True Production Observability & Security
- **OpenTelemetry & Jaeger**: Dexo emits full distributed traces via OTLP, allowing you to visually debug exactly what LangGraph and the LLMs are doing in the Jaeger UI.
- **RBAC (Role-Based Access Control)**: The JWT security middleware ensures API endpoints enforce strict role-based scopes (e.g. `src:write`).

### 4. Advanced Tooling (MCP & Playwright)
- **Model Context Protocol (MCP)**: Dexo interfaces with standardized MCP servers, meaning it can securely interact with filesystems, Git, or external APIs using the exact same standard that Claude Desktop uses.
- **Agentic Browsing**: With Playwright built directly into the Dockerfile, Dexo has the capacity to spin up headless Chromium instances and actually navigate the web to perform research.

### 5. World-Class CI/CD Pipeline
- **Docker & GitHub Container Registry**: Infrastructure automatically builds Docker images, runs them through the Trivy Vulnerability Scanner to guarantee enterprise security compliance, and publishes them to GHCR.
- **Developer Ergonomics**: The Makefile abstracts all the complexity away, and the NPM CLI Wrapper (`dexo start --user "..."`) makes consuming the agent as easy as running a native terminal command.

## 🛠️ Tech Stack

- **Package Manager**: `uv`
- **Orchestration**: LangGraph, LangChain
- **API Framework**: FastAPI
- **Security**: python-jose (JWT), Pydantic Settings
- **Testing**: Pytest, Respx, Coverage (>= 80% enforced)

## 📦 Getting Started

### 1. Prerequisites

- Python 3.12+
- `uv` package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Optional: Zep server, Mem0 API key, Ollama installed locally

### 2. Installation

1. Install dependencies using `uv`:
   ```bash
   uv sync --all-groups
   ```
2. Set up your environment variables:
   ```bash
   cp .env.example .env
   ```
3. Populate `.env` with your API keys and config (Note: lists like `COMMAND_ALLOWLIST` must be valid JSON strings, e.g., `'["git", "ls"]'`).

### 3. Usage & Makefile Commands

We use a standard `Makefile` to streamline daily operations:

- **Run Dev Server**:
  ```bash
  make dev
  ```
- **Run Tests** (with Coverage report):
  ```bash
  make test
  ```
- **Linting & Formatting**:
  ```bash
  make lint
  make format
  ```
- **Type Checking**:
  ```bash
  make typecheck
  ```

## 🏗️ Project Structure

```text
/
├── /api
│   └── index.py            # Vercel Serverless Function entrypoint
├── /src                    # Core python package
│   ├── /assets             # Prompts, rules (AGENTS.md), skills, and MCP configs
│   ├── /config.py          # Pydantic BaseSettings
│   ├── /context            # Context loaders for assets, rules, and MCP
│   ├── /graph              # LangGraph nodes, state definitions, and builder
│   ├── /main.py            # FastAPI Application
│   ├── /memory             # Zep, Mem0, Postgres fusion manager
│   ├── /observability      # OpenTelemetry & structlog JSON formatting
│   ├── /providers          # LLM Factory (Ollama, Gemini, OpenAI)
│   ├── /security           # JWT, Middleware, and RBAC
│   └── /tools              # Modular tools (Browser, Fetch, Run Command, etc.)
├── Makefile
├── pyproject.toml
└── vercel.json             # Vercel routing configuration
```

## ☁️ Deployment

This orchestrator is optimized for deployment on Vercel as a Serverless Function.

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/emfhal/dexo&env=OPENAI_API_KEY,ANTHROPIC_API_KEY,GEMINI_API_KEY,DATABASE_URL)

1. Ensure your `.env` variables are uploaded to your Vercel Project settings (including your `GEMINI_API_KEY`).
2. We highly recommend turning off `LOG_PRETTY` in production so logs are streamed as structured JSON:
   ```env
   LOG_PRETTY=false
   LOG_LEVEL=INFO
   ```
3. Link your project from Vercel and deploy!
   ```bash
   vercel link
   vercel --prod
   ```

## 🔒 Security Practices

- **Pre-push hooks**: Ensure type checking (`mypy`), linting (`ruff`), and testing coverage pass before any code is pushed to production.
- **SSRF Prevention**: `fetch_website` prevents requests resolving to internal networks (CIDR blocks configurable in `.env`).
- **Command Safety**: The shell command tool operates on a strict allowlist. It is impossible for the orchestrator to arbitrarily execute unverified binaries.

## 🤝 Contributing

First off, thank you for considering contributing to Dexo! It's people like you that make open-source software such a great community to learn, inspire, and create.

To ensure a smooth workflow and clean history, we strictly enforce an issue-driven workflow. Please read through these guidelines before submitting a Pull Request.

### 1. Open an Issue First

**Do not write any code before opening an issue.** 

To maintain a clean and trackable project history, every Pull Request must be tied to an open issue. 
1. Go to the [Issues page](https://github.com/emfhal/dexo/issues) and open a new issue describing the bug you want to fix or the feature you want to build.
2. Wait for a maintainer to approve or assign the issue to you.
3. Take note of the **Issue Number** (e.g., `#1`). You will use this number (e.g., `DEXO-1`) as your prefix for all branches and commits.

### 2. Local Setup

Once you have your issue number, fork the repository and clone it locally:

```bash
git clone git@github.com:<your-username>/dexo.git
cd dexo
git remote add upstream git@github.com:emfhal/dexo.git
```

Set up the environment using `uv`:
```bash
uv sync --all-groups
cp .env.example .env
```

### 3. Branching and Committing

Create a feature branch prefixed with your issue number. For example, if you are working on Issue #1:
```bash
git checkout -b DEXO-1-add-amazing-feature
```

As you make changes, ensure your commit messages also follow the strict prefix convention:
```bash
git commit -m "DEXO-1 - Add amazing feature"
```

**Regex Validation:**
If you configure a local git hook (like `commit-msg`), you can use the following regular expression to validate your commit messages:
```regex
^DEXO-\d+ - .+$
```

### 4. Testing and Linting

Before opening a Pull Request, you must ensure your code passes all formatting, linting, and testing checks. Our `Makefile` provides commands for this:

```bash
make format
make lint
make typecheck
make test
```

### 5. Opening a Pull Request

1. Fetch the latest changes from upstream and rebase to ensure a clean, linear history:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```
2. Push your branch to your fork:
   ```bash
   git push -u origin DEXO-1-add-amazing-feature
   ```
3. Open a Pull Request on the main repository. In the PR description, explicitly reference the issue it resolves so GitHub links them automatically (e.g., `Resolves #1`).

Maintainers will review your PR. Once approved, it will be squash-merged into the `main` branch. 

Happy coding!

## 📜 License

This project is open-source and licensed under the **Apache License 2.0** - see the [LICENSE](LICENSE) file for details.
