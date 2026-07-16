# ─────────────────────────────────────────────────────────────────────────────
#  LangGraph Agent v2 — Makefile (uv-first)
#  All Python commands run inside `uv run` so no manual venv activation needed.
# ─────────────────────────────────────────────────────────────────────────────

.DEFAULT_GOAL := help
UV := uv
PYTHON := $(UV) run python
PYTEST := $(UV) run pytest
RUFF   := $(UV) run ruff
MYPY   := $(UV) run mypy

# Colours
CYAN  := \033[36m
RESET := \033[0m

.PHONY: help install sync dev lint format typecheck test test-fast \
        clean docker-up docker-down ollama-pull gemini-test \
        db-migrate assets-check

# ── Help ──────────────────────────────────────────────────────────────────────
help: ## Show this help message
	@echo ""
	@echo "  LangGraph Agent v2 — uv-native commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-22s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ── Installation ──────────────────────────────────────────────────────────────
install: ## Create venv and install all deps (including dev) via uv
	$(UV) sync --all-groups
	@echo "✅  Virtual environment ready at .venv/"

sync: ## Sync deps without re-locking (faster after pyproject.toml changes)
	$(UV) sync

upgrade: ## Upgrade all dependencies and regenerate uv.lock
	$(UV) lock --upgrade
	$(UV) sync --all-groups

playwright-install: ## Install Playwright Chromium browser binary
	$(UV) run playwright install chromium

# ── Development server ────────────────────────────────────────────────────────
dev: ## Run FastAPI with hot-reload (development)
	$(UV) run uvicorn src.main:app \
	  --host 0.0.0.0 --port 8080 \
	  --reload --reload-dir src \
	  --log-level debug

dev-prod: ## Run FastAPI in production mode (no reload)
	$(UV) run uvicorn src.main:app \
	  --host 0.0.0.0 --port 8080 \
	  --workers 4 --log-level info

# ── Code quality ──────────────────────────────────────────────────────────────
lint: ## Run ruff linter (check only)
	$(RUFF) check src/

format: ## Auto-fix lint issues and format code
	$(RUFF) format src/
	$(RUFF) check --fix src/

typecheck: ## Run mypy static type checking
	$(MYPY) src/

check: lint typecheck ## Run all quality checks

# ── Testing ───────────────────────────────────────────────────────────────────
test: ## Run full test suite with coverage
	$(PYTEST) src/ \
	  --cov=src \
	  --cov-report=term-missing \
	  --cov-report=html:htmlcov

test-fast: ## Run tests (no coverage, parallel)
	$(PYTEST) src/ -x -q

test-watch: ## Run tests in watch mode (requires pytest-watch)
	$(UV) run ptw src/ -- -x -q

# ── LLM Providers ────────────────────────────────────────────────────────────
ollama-pull: ## Pull the default Ollama models (gemma3:27b + nomic-embed-text)
	ollama pull gemma3:27b
	ollama pull nomic-embed-text
	ollama pull llama3.2:3b  # small fallback model

ollama-status: ## Check running Ollama models
	ollama list

gemini-test: ## Quick sanity-check that GEMINI_API_KEY works
	$(PYTHON) -c "\
from langchain_google_genai import ChatGoogleGenerativeAI; \
m = ChatGoogleGenerativeAI(model='gemini-2.0-flash'); \
print(m.invoke('Say hi').content)"

openai-test: ## Quick sanity-check for OpenAI key
	$(PYTHON) -c "\
from langchain_openai import ChatOpenAI; \
m = ChatOpenAI(model='gpt-4o-mini'); \
print(m.invoke('Say hi').content)"

# ── Assets ────────────────────────────────────────────────────────────────────
assets-check: ## Validate all SKILL.md files have required frontmatter
	$(PYTHON) -c "\
from src.context.sources.skills import load_skills; \
skills = load_skills('src/assets/skills'); \
subagent_skills = load_skills('src/assets/subagents'); \
all_skills = skills + subagent_skills; \
print(f'✅  {len(all_skills)} skills found:'); \
[print(f'   • {s[\"name\"]}') for s in all_skills]"

assets-list: ## List all asset directories
	@echo "\n── Skills ──"; ls src/assets/skills/
	@echo "\n── Subagents ──"; ls src/assets/subagents/
	@echo "\n── Rules ──"; ls src/assets/rules/
	@echo "\n── Prompts ──"; ls src/assets/prompts/
	@echo "\n── MCP Servers ──"; cat src/assets/mcp/servers.json | python3 -c "import sys,json; [print('   •', s['name']) for s in json.load(sys.stdin)]"

# ── Docker ────────────────────────────────────────────────────────────────────
docker-up: ## Start all backing services (Postgres, Zep, Jaeger, Ollama)
	docker compose up -d
	@echo "✅  Services running. Jaeger UI: http://localhost:16686"

docker-down: ## Stop all backing services
	docker compose down

docker-logs: ## Follow logs for all services
	docker compose logs -f

docker-reset: ## Tear down + delete volumes (destructive!)
	docker compose down -v --remove-orphans

# ── Database ──────────────────────────────────────────────────────────────────
db-migrate: ## Apply LangGraph checkpoint DDL to Postgres
	$(PYTHON) -c "\
import asyncio; \
from src.memory.backends.postgres import PostgresMemoryBackend; \
from src.config import get_settings; \
b = PostgresMemoryBackend(get_settings().database); \
asyncio.run(b.setup_schema())"

db-shell: ## Open psql shell to the local Postgres
	docker compose exec postgres psql -U agent -d agent_db

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean: ## Remove caches and build artefacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name "htmlcov"     -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete 2>/dev/null; true
	@echo "✅  Cleaned."

# ── CI shortcut ───────────────────────────────────────────────────────────────
ci: install lint typecheck test ## Full CI pipeline
