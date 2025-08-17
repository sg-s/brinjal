# brinjal/Makefile

.PHONY: install dev test clean lint format docs

# Install dependencies
install:
	uv sync

# Run the FastAPI app in development mode
dev:
	uv run uvicorn brinjal.main:app --host 0.0.0.0 --port 8000 --reload

# Run tests
test:
	uv run pytest

# Clean up
clean:
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/

# Lint code
lint:
	uv run ruff check .

# Format code
format:
	uv run ruff format .

# Serve documentation
docs:
	uv run mkdocs serve --dev-addr=0.0.0.0:8080
