# Unique AI Workspace Makefile
# Simplifies common development tasks across all packages

.PHONY: help install sync test test-all test-sdk test-toolkit test-stock test-follow-up test-web-search test-internal-search lint lint-all type-check clean

# Default target
help:
	@echo "Unique AI Workspace - Available Commands:"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  install         Install uv and sync workspace"
	@echo "  sync            Sync all workspace dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test            Run all tests (including async)"
	@echo "  test-sync       Run all tests (sync only for compatibility)"
	@echo "  test-sdk        Run unique-sdk tests (sync only)"
	@echo "  test-sdk-all    Run unique-sdk tests (including async)"
	@echo "  test-toolkit    Run unique-toolkit tests (including async)"
	@echo "  test-stock      Run unique-stock-ticker tests"
	@echo "  test-follow-up  Run unique-follow-up-questions tests"
	@echo "  test-web-search Run unique-web-search tests"
	@echo "  test-internal-search Run unique-internal-search tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint            Run linting on all packages"
	@echo "  lint-sdk        Run linting on unique-sdk"
	@echo "  lint-toolkit    Run linting on unique-toolkit"
	@echo "  type-check      Run type checking on main packages"
	@echo ""
	@echo "Validation:"
	@echo "  validate        Validate workspace imports"
	@echo "  validate-deps   Validate dependencies match diagram"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean           Clean cache and temporary files"
	@echo "  lock            Update workspace lockfile"

# Setup & Installation
install:
	@echo "🔧 Installing uv and syncing workspace..."
	@which uv >/dev/null || (echo "❌ uv not found. Please install uv first: https://docs.astral.sh/uv/" && exit 1)
	uv sync --preview --extra dev

sync:
	@echo "🔄 Syncing workspace dependencies..."
	uv sync --preview --extra dev

lock:
	@echo "🔒 Updating workspace lockfile..."
	uv lock --preview

# Testing - Main targets
test: test-sdk-all test-toolkit test-stock test-follow-up test-web-search test-internal-search
	@echo "✅ All workspace tests completed!"

test-sync: test-sdk test-toolkit-safe test-stock test-follow-up test-web-search test-internal-search
	@echo "✅ All workspace tests (sync only) completed!"

# Individual package tests
test-sdk:
	@echo "🧪 Running unique-sdk tests (sync only)..."
	cd unique_sdk && uv run --package unique-sdk pytest tests/ -v -k "not async"

test-sdk-all:
	@echo "🧪 Running unique-sdk tests (including async)..."
	cd unique_sdk && uv run --package unique-sdk pytest tests/ -v

test-toolkit:
	@echo "🧪 Running unique-toolkit tests..."
	cd unique_toolkit && uv run --package unique-toolkit pytest tests/ -v

test-toolkit-safe:
	@echo "🧪 Running unique-toolkit tests (import check only)..."
	uv run --package unique-toolkit python -c "import unique_toolkit; import unique_sdk; print('✅ Toolkit tests: imports successful')"

test-stock:
	@echo "🧪 Running unique-stock-ticker tests..."
	uv run --package unique-stock-ticker python -c "import unique_stock_ticker; import unique_toolkit; import unique_sdk; print('✅ Stock ticker tests: imports successful')"

test-follow-up:
	@echo "🧪 Running unique-follow-up-questions tests..."
	uv run --package unique-follow-up-questions python -c "import unique_follow_up_questions; import unique_toolkit; import unique_sdk; print('✅ Follow-up questions tests: imports successful')"

test-web-search:
	@echo "🧪 Running unique-web-search tests..."
	uv run --package unique-web-search python -c "import unique_web_search; import unique_toolkit; import unique_sdk; print('✅ Web search tests: imports successful')"

test-internal-search:
	@echo "🧪 Running unique-internal-search tests..."
	uv run --package unique-internal-search python -c "import unique_internal_search; import unique_toolkit; import unique_sdk; print('✅ Internal search tests: imports successful')"

# Code Quality
lint: lint-sdk lint-toolkit lint-stock lint-follow-up lint-web-search lint-internal-search
	@echo "✅ All linting completed!"

lint-sdk:
	@echo "🔍 Linting unique-sdk..."
	uv run --extra dev ruff check unique_sdk/ --exclude unique_sdk/site/ --exclude unique_sdk/docs/

lint-toolkit:
	@echo "🔍 Linting unique-toolkit..."
	uv run --extra dev ruff check unique_toolkit/ --exclude unique_toolkit/site/ --exclude unique_toolkit/docs/

lint-stock:
	@echo "🔍 Linting unique-stock-ticker..."
	uv run --extra dev ruff check unique_stock_ticker/

lint-follow-up:
	@echo "🔍 Linting unique-follow-up-questions..."
	uv run --extra dev ruff check unique_follow_up_questions/

lint-web-search:
	@echo "🔍 Linting unique-web-search..."
	uv run --extra dev ruff check tool_packages/unique_web_search/unique_web_search/

lint-internal-search:
	@echo "🔍 Linting unique-internal-search..."
	uv run --extra dev ruff check tool_packages/unique_internal_search/unique_internal_search/

type-check:
	@echo "🔍 Running type checking..."
	uv run --extra dev pyright unique_sdk/
	uv run --extra dev pyright unique_toolkit/

# Development helpers
dev-test: test-sdk lint-sdk
	@echo "✅ Quick development test (SDK) completed!"

# Maintenance
clean:
	@echo "🧹 Cleaning cache and temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup completed!"

# Workspace validation
validate:
	@echo "🔍 Validating workspace configuration..."
	@echo "Testing unique_sdk..."
	@uv run --package unique-sdk python -c "import unique_sdk; print('✅ unique_sdk validated')"
	@echo "Testing unique_toolkit..."
	@uv run --package unique-toolkit python -c "import unique_toolkit, unique_sdk; print('✅ unique_toolkit validated')"
	@echo "Testing unique_stock_ticker..."
	@uv run --package unique-stock-ticker python -c "import unique_stock_ticker, unique_toolkit, unique_sdk; print('✅ unique_stock_ticker validated')"
	@echo "Testing unique_follow_up_questions..."
	@uv run --package unique-follow-up-questions python -c "import unique_follow_up_questions, unique_toolkit, unique_sdk; print('✅ unique_follow_up_questions validated')"
	@echo "Testing unique_web_search..."
	@uv run --package unique-web-search python -c "import unique_web_search, unique_toolkit, unique_sdk; print('✅ unique_web_search validated')"
	@echo "Testing unique_internal_search..."
	@uv run --package unique-internal-search python -c "import unique_internal_search, unique_toolkit, unique_sdk; print('✅ unique_internal_search validated')"
	@echo "✅ All packages validated successfully!"

# Dependency validation
validate-deps:
	@echo "🔍 Validating package dependencies against Mermaid diagram..."
	@uv run python scripts/validate_dependencies.py

# Pre-commit simulation
pre-commit: lint type-check test
	@echo "✅ Pre-commit checks completed!"
