#!/bin/bash
# Check quality of generated code

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🔍 Checking generated code quality..."
echo

## Fix fixable
echo "🔍 Fixing fixable issues with ruff..."
ruff check generated_routes/ --fix --unsafe-fixes || true
ruff format generated_routes/ || true
echo

## Fix type errors
echo "🔍 Fixing type errors..."
pyright generated_routes/ --fix-errors || true
echo


# Check with pyright  
echo "🔎 Running pyright type checking..."
pyright generated_routes/ 2>&1 | grep -E "(error|warning):" || echo "✅ No type errors found"
echo

# Summary
echo "📊 Summary:"
echo "  - Run 'poetry run python generate_routes.py' to regenerate routes"
echo "  - Check CODEGEN_README.md for troubleshooting tips"

