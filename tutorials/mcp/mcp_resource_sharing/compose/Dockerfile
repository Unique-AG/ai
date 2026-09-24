# Build context: mcp_resource_sharing/ (the uv project root)
# Usage: docker compose -f compose/docker-compose.yml build
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base

WORKDIR /app

# Copy only the dependency manifest first for layer caching.
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source and install the project into the venv.
COPY src/ ./src/
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
