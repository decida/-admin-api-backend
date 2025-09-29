.PHONY: install run test lint format db-create db-drop docker-up docker-down clean

# Install dependencies
install:
	poetry install

# Run development server
run:
	poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
test:
	poetry run pytest

# Lint code
lint:
	poetry run ruff check app/
	poetry run mypy app/

# Format code
format:
	poetry run black app/
	poetry run ruff check --fix app/

# Create database schema (via Docker)
db-create:
	docker exec -i admin-api-db psql -U admin -d admindb < sql/001_create_databases_table.sql

# Drop database schema (via Docker)
db-drop:
	docker exec -i admin-api-db psql -U admin -d admindb < sql/999_drop_all.sql

# Start Docker containers
docker-up:
	docker-compose up -d

# Stop Docker containers
docker-down:
	docker-compose down

# Clean cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +