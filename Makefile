# brinjal/Makefile

.PHONY: install dev test test-fast test-slow clean lint format docs build

# Install dependencies
install:
	uv sync

# Run the FastAPI app in development mode
dev:
	uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload


# Run all tests
test:
	uv run pytest

# Run fast tests only (exclude slow tests)
test-fast:
	uv run pytest -m "not slow"

# Run slow tests only
test-slow:
	uv run pytest -m "slow"

# Run specific test file
test-task-manager:
	uv run pytest tests/test_task_manager.py -v

test-example-task:
	uv run pytest tests/test_example_task.py -v

# Run tests with coverage
test-cov:
	uv run pytest --cov=brinjal --cov-report=html --cov-report=term

# Clean up
clean:
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf htmlcov/
	rm -rf .coverage

# Lint code
lint:
	uv run ruff check .

# Format code
format:
	uv run ruff format .

# Serve documentation
docs:
	uv run mkdocs serve --dev-addr=0.0.0.0:8080

# Build package
build:
	uv run python -m build
	@echo "Package built successfully!"
	@echo "Check dist/ directory for wheel and source distribution"
