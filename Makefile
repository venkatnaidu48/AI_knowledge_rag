# RAG Application Makefile
# Convenient commands for development, testing, and deployment

.PHONY: help install setup dev test test-unit test-integration test-performance lint format clean docker-up docker-down docs run

help:
	@echo "RAG Application - Available Commands"
	@echo "===================================="
	@echo "make install          - Install dependencies"
	@echo "make setup            - Setup development environment"
	@echo "make dev              - Run development server"
	@echo "make test             - Run all tests"
	@echo "make test-unit        - Run unit tests only"
	@echo "make test-integration - Run integration tests only"
	@echo "make test-performance - Run performance tests"
	@echo "make lint             - Run code linter (flake8)"
	@echo "make format           - Format code (black)"
	@echo "make clean            - Clean temporary files"
	@echo "make docker-up        - Start Docker services"
	@echo "make docker-down      - Stop Docker services"
	@echo "make docs             - Generate documentation"
	@echo "make run              - Run production server"

install:
	pip install -r requirements.txt

setup: install
	@echo "Creating necessary directories..."
	mkdir -p data/uploads logs backups
	@echo "Setup complete!"

dev:
	python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest -v

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-performance:
	pytest tests/performance/ -v

lint:
	flake8 src/ tests/ --max-line-length=120 --exclude=__pycache__

format:
	black src/ tests/ --line-length=120

clean:
	@echo "Cleaning temporary files..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete!"

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docs:
	@echo "Documentation is in docs/ directory"
	@echo "View ARCHITECTURE_DIAGRAM.md for system design"

run:
	python -m uvicorn src.main:app --host 0.0.0.0 --port 8000

.DEFAULT_GOAL := help
