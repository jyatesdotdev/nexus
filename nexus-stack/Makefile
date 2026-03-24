.PHONY: build up down test chat logs clean

# Default target
all: build up

build:
	@echo "🔨 Building Docker images..."
	docker compose build

up:
	@echo "🚀 Starting all services..."
	docker compose up -d

down:
	@echo "🛑 Stopping all services..."
	docker compose down

test:
	@echo "🧪 Running Orchestrator Tests..."
	docker compose run --rm -e PYTHONPATH=/app orchestrator pytest /app/test_orchestrator.py /app/test_ollama_adapter.py -v
	@echo "🧪 Running A2A Integration Tests..."
	docker compose run --rm -e PYTHONPATH=/app orchestrator pytest /e2e_tests/test_a2a_integration.py -v
	@echo "🧪 Running Frontend Tests..."
	cd ../nexus-ui && npm test

chat:
	@echo "💬 Starting Interactive CLI Chat..."
	docker compose run --rm orchestrator python main.py

logs:
	@echo "📋 Tailing logs..."
	docker compose logs -f

clean: down
	@echo "🧹 Cleaning up containers and dangling images..."
	docker system prune -f
