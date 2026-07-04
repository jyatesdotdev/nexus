.PHONY: build up down test lint type-check chat logs clean verify-all

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

test:
	@echo "🧪 Running Unit Tests..."
	# EDUCATIONAL NOTE: We run unit tests for all microservices to ensure individual component integrity.
	cd ../nexus-orchestrator && PYTHONPATH=. ./venv/bin/pytest tests/
	cd ../nexus-mcp && PYTHONPATH=. ../nexus-orchestrator/venv/bin/python -m pytest tests/
	cd ../nexus-a2a && PYTHONPATH=. ../nexus-orchestrator/venv/bin/python -m pytest tests/
	cd ../nexus-ui && npm test -- --run

	@echo "🧪 Running Integration Tests..."
	# EDUCATIONAL NOTE: Integration tests verify that services can communicate correctly over the network.
	docker compose run --rm -e PYTHONPATH=/app orchestrator pytest /e2e_tests/test_a2a_integration.py /e2e_tests/test_persistence_integration.py -v

test-e2e: up
	@echo "🎭 Running Playwright E2E Tests..."
	# EDUCATIONAL NOTE: E2E tests verify the frontend's interaction with the live Docker backend.
	cd ../nexus-ui && npx playwright install --with-deps chromium && npm run test:e2e

lint:
	@echo "🧹 Running Linters (Ruff & ESLint)..."
	# EDUCATIONAL NOTE: Consistent styling and bug prevention via static analysis.
	cd ../nexus-orchestrator && ./venv/bin/ruff check .
	cd ../nexus-mcp && ../nexus-orchestrator/venv/bin/python -m ruff check .
	cd ../nexus-a2a && ../nexus-orchestrator/venv/bin/python -m ruff check .
	cd ../nexus-ui && npm run lint

type-check:
	@echo "⌨️ Running Type Checkers (Mypy & TSC)..."
	# EDUCATIONAL NOTE: Enforcing static types reduces runtime errors and improves documentation.
	cd ../nexus-orchestrator && ./venv/bin/mypy .
	cd ../nexus-mcp && ../nexus-orchestrator/venv/bin/python -m mypy .
	cd ../nexus-a2a && ../nexus-orchestrator/venv/bin/python -m mypy .
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
	@echo "🧹 Cleaning up containers and dangling images..."
	# EDUCATIONAL NOTE: System prune is used to prevent storage bloat from unused build layers.
	docker system prune -f
