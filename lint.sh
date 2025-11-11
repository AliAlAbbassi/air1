#!/bin/bash

# Lint and check Python code

echo "=== Python Compilation Check ==="
uv run python -m compileall air1/

echo -e "\n=== Linting with Ruff ==="
uv run ruff check --fix air1/

# Let PyCharm handle formatting
# echo -e "\n=== Formatting ==="
# echo "Use PyCharm's Reformat Code (Cmd+Option+L on Mac, Ctrl+Alt+L on Windows/Linux)"

# Optional: Add mypy type checking
# echo -e "\n=== Type Checking with mypy ==="
# uv run mypy air1/

echo -e "\nDone!"