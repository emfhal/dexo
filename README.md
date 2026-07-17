# Dexo - Enterprise LangGraph Orchestrator

<div align="center">
  <img src="./assets/logo.svg" width="200" alt="Dexo Logo" />
</div>

A robust, frontier-grade multi-agent architecture powered by LangGraph, FastAPI, and OpenTelemetry. Designed for high scalability, observability, and modular tool integration. The codebase follows standard Python packaging (`src/` layout) and is deployment-ready for Vercel Serverless Functions.

## 🚀 Features

- **Multi-Provider LLM Registry**: Seamless switching between Ollama (local), Gemini, OpenAI, and Anthropic. Configurable fallback models for robust execution.
- **Advanced Context & Memory Fusion**: 
  - **Zep**: Semantic long-term memory, conversation summarization, and entity extraction.
  - **Mem0**: Personalization and persistent user-fact profiling.
  - **Postgres (pgvector)**: Fast, local vector searches and checkpoint state persistence.
- **Modular Asset Architecture**: Skills, Subagents, Rules, and Prompts are cleanly isolated in the `assets/` directory.
- **Enterprise Observability**: Integrated OpenTelemetry (OTLP) tracking for LangChain/LangGraph instrumentations and HTTP requests.
- **Secure Sandboxing**: JWT-based Authentication & RBAC out of the box. Configurable SSRF protection and restricted shell command execution (`COMMAND_ALLOWLIST`).
- **Slim Serverless Vercel Deployment**: Pre-configured `api/index.py` entrypoint and `vercel.json` routing.

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
