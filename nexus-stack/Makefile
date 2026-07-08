.PHONY: build up down doctor demo test test-e2e lint type-check chat logs evals clean clean-all verify-all new-agent

# EDUCATIONAL NOTE: The Makefile abstracts complex Docker Compose commands, providing 
# a simplified interface for developers and ensuring consistent environment management.

# Default target
all: build up

build:
	@echo "🔨 Building UI locally to avoid Docker OOM limits..."
	cd ../nexus-ui && npm install && npm run build
	@echo "🔨 Building Docker images..."
	# EDUCATIONAL NOTE: Using --parallel (default in newer Docker) to speed up multi-service builds.
	docker compose build

up:
	@echo "🌐 Ensuring shared network exists..."
	docker network create nexus-net || true
	@echo "🏗️ Starting infrastructure services..."
	cd ../nexus-dev-infra && docker compose up -d
	@echo "🚀 Starting application services..."
	# EDUCATIONAL NOTE: Starting in detached mode to keep the terminal free.
	docker compose up -d

down:
	@echo "🛑 Stopping application services..."
	# EDUCATIONAL NOTE: Removing volumes on down is optional, but 'down' ensures a clean stop.
	docker compose down
	@echo "🛑 Stopping infrastructure services..."
	cd ../nexus-dev-infra && docker compose down

doctor:
	@echo "🩺 Running preflight checks..."
	# EDUCATIONAL NOTE: A preflight target catches missing prerequisites (Docker,
	# .env, network, Node) with actionable guidance BEFORE a long 'make up' fails.
	@bash scripts/doctor.sh

demo:
	@echo "🎬 Running guided demo conversation..."
	# EDUCATIONAL NOTE: The demo sends canned prompts that exercise each delegation
	# path (MCP, A2A, local tools) and prints trace IDs linked to Grafana Tempo.
	@bash scripts/demo.sh

test:
	@echo "🧪 Running Unit Tests..."
	# EDUCATIONAL NOTE: We run unit tests for all microservices to ensure individual component integrity.
	# One `uv sync` at the workspace root materializes a single shared .venv for
	# all four Python projects; `--no-sync` on the per-service runs then reuses it
	# instead of re-resolving each service's subset of the environment.
	cd .. && uv sync
	cd ../nexus-orchestrator && uv run --no-sync pytest tests/
	cd ../nexus-mcp && uv run --no-sync pytest tests/
	cd ../nexus-a2a && uv run --no-sync pytest tests/
	cd ../nexus-ui && npm test -- --run

	@echo "🧪 Running Integration Tests..."
	# EDUCATIONAL NOTE: Integration tests verify that services can communicate correctly over the network.
	# Pointing pytest at the mounted directory (not an explicit file list) lets its
	# default test_*.py discovery pick up new nexus-integration tests automatically.
	docker compose run --rm -e PYTHONPATH=/app orchestrator pytest /e2e_tests -v

test-e2e: up
	@echo "🎭 Running Playwright E2E Tests..."
	# EDUCATIONAL NOTE: E2E tests verify the frontend's interaction with the live Docker backend.
	cd ../nexus-ui && npx playwright install --with-deps chromium && npm run test:e2e

lint:
	@echo "🧹 Running Linters (Ruff & ESLint)..."
	# EDUCATIONAL NOTE: Consistent styling and bug prevention via static analysis.
	cd .. && uv sync
	cd .. && uv run --no-sync ruff check nexus-a2a nexus-common nexus-mcp nexus-orchestrator
	cd ../nexus-ui && npm run lint

type-check:
	@echo "⌨️ Running Type Checkers (Mypy & TSC)..."
	# EDUCATIONAL NOTE: Enforcing static types reduces runtime errors and improves documentation.
	cd .. && uv sync
	cd ../nexus-orchestrator && uv run --no-sync mypy .
	cd ../nexus-mcp && uv run --no-sync mypy .
	cd ../nexus-a2a && uv run --no-sync mypy .
	cd ../nexus-common && uv run --no-sync mypy .
	cd ../nexus-ui && npm run type-check

chat:
	@echo "💬 Starting Interactive CLI Chat..."
	# EDUCATIONAL NOTE: Interactive mode (tty/stdin) is enabled to allow the LLM to 
	# communicate directly with the user in the terminal.
	docker compose run --rm orchestrator python main.py

logs:
	@echo "📋 Tailing logs..."
	docker compose logs -f

evals:
	@echo "🧪 Running Nexus LLM Evaluations..."
	# EDUCATIONAL NOTE: LLM Evals measure non-deterministic performance (routing & accuracy)
	# by running a large batch of prompts through the orchestrator.
	docker compose run --rm orchestrator python main.py evals

verify-all: lint type-check evals
	@echo "🔍 Running Nexus Standards Verification (via Semgrep & Checkov)..."
	# EDUCATIONAL NOTE: Using standard tools (Semgrep, Checkov) via Docker 
	# ensures that our standards enforcement is portable, version-controlled, 
	# and consistent across all developer machines and CI/CD pipelines.
	
	@echo "🧵 Checking Architectural Standards (Semgrep)..."
	# EDUCATIONAL NOTE: Semgrep is used to enforce custom patterns (like educational notes) 
	# by scanning code structure across all repositories.
	docker run --rm -v $(PWD)/..:/src returntocorp/semgrep semgrep scan --config=/src/nexus-stack/.semgrep.yaml --error
	
	@echo "🛡️ Checking Production Readiness (Checkov)..."
	# EDUCATIONAL NOTE: Checkov ensures our Dockerfiles follow best practices 
	# (multi-stage builds, non-root users) without us having to write custom rules.
	docker run --rm -v $(PWD)/..:/src bridgecrew/checkov --directory /src --check CKV_DOCKER_11,CKV_DOCKER_7 --quiet

clean: down
	@echo "🧹 Removing Nexus-built images and reclaiming build cache..."
	# EDUCATIONAL NOTE: Scoped cleanup. 'down --rmi local' removes only the images
	# these two compose projects built (pulled infra images like postgres/grafana
	# are kept — cheap to re-pull). The dangling-image and build-cache prunes are
	# machine-wide but always safe: they delete unreferenced garbage, costing only
	# rebuild time, never data. The previous 'docker system prune' here also
	# deleted OTHER projects' stopped containers — a machine-wide side effect this
	# target deliberately avoids. Data volumes are untouched; see 'clean-all'.
	docker compose down --rmi local --remove-orphans
	cd ../nexus-dev-infra && docker compose down --rmi local --remove-orphans
	docker image prune -f
	docker builder prune -f

clean-all:
	# EDUCATIONAL NOTE: Destructive operations should demand explicit intent — an
	# env-var gate (FORCE=1) works for both humans and automation, unlike an
	# interactive prompt which hangs headless callers.
	@if [ "$(FORCE)" != "1" ]; then \
		echo "⚠️  clean-all additionally DELETES the Nexus data volumes:"; \
		echo "   Postgres history, Redis sessions, Grafana state — unrecoverable."; \
		echo "   If that is what you want, re-run as: make clean-all FORCE=1"; \
		exit 1; \
	fi
	$(MAKE) clean
	@echo "🗑️  Removing Nexus data volumes..."
	docker compose down -v
	cd ../nexus-dev-infra && docker compose down -v

new-agent:
	# EDUCATIONAL NOTE: Turns the manual "Adding a New Service" checklist into a
	# two-minute operation: copies templates/a2a-service to ../nexus-$(NAME),
	# substitutes name/port tokens, and prints the remaining wiring steps
	# (compose entry, A2A_AGENT_URLS, Prometheus, uv workspace) instead of
	# editing those shared files automatically.
	@bash scripts/new-agent.sh "$(NAME)" "$(PORT)"
