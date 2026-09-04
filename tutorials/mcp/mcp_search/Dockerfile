# ============================================================================
# MCP Search Application Dockerfile
# ============================================================================

# -----------------------------------------------------------------------------
# Build stage
# -----------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:0.12.9-python3.12-trixie-slim@sha256:531264df5767959a4981eaacbd88768e3bbc2a10ad581939b62953118701fa66 AS builder

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy dependency files first (for better caching)
COPY pyproject.toml ./

# Install dependencies from PyPI. --no-sources ignores the editable path
# sources for unique-mcp / unique-toolkit (which live outside this build
# context in the monorepo) so the image can be built standalone, e.g. with
# `az acr build` from this directory.
# Explicit .devN pins in pyproject are enough for prereleases (uv default
# prerelease mode is if-necessary-or-explicit); no --prerelease=allow.
RUN uv lock --no-sources && \
    uv sync --frozen --no-install-project --no-dev

# Copy the application source code
COPY . .

# Install the project itself
RUN uv sync --frozen --no-dev

# -----------------------------------------------------------------------------
# Runtime stage
# -----------------------------------------------------------------------------
FROM python:3.14-slim-trixie@sha256:cad9a2c871761c413caa6fdd6441c783451e740a48aaeba60ae62a8b53525ef6 AS runtime

WORKDIR /app

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home appuser

# Copy the virtual environment from the builder
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv

# Copy the application source
COPY --from=builder --chown=appuser:appgroup /app/src /app/src

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Set Python environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8003/health')" || exit 1

# Run the application
CMD ["python", "-m", "mcp_search.mcp_search_server"]
