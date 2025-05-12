.PHONY: install test lint format clean run

# Install the package and dependencies
install:
	poetry install

# Run the tests
test:
	poetry run pytest

# Run the linter
lint:
	poetry run flake8 discord_mcp_bot tests
	poetry run isort --check-only discord_mcp_bot tests

# Format the code
format:
	poetry run black discord_mcp_bot tests
	poetry run isort discord_mcp_bot tests

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Run the bot
run:
	poetry run python -m discord_mcp_bot.main