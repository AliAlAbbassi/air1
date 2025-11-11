#!/bin/bash

# Check if Python code compiles

echo "Checking Python compilation..."

# Check all Python files
uv run python -m compileall air1/

# Check specific file if provided as argument
if [ $# -eq 1 ]; then
    echo "Checking $1..."
    uv run python -m py_compile "$1"
fi

echo "Done!"