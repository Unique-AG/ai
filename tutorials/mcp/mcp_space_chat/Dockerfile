# ============================================================================
# MCP Space Chat Application Dockerfile
# ============================================================================

# -----------------------------------------------------------------------------
# Build stage
# -----------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim@sha256:e5b65587bce7de595f299855d7385fe7fca39b8a74baa261ba1b7147afa78e58 AS builder

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy dependency files first (for better caching)
COPY pyproject.toml ./

# Install dependencies from PyPI. --no-sources ignores the editable path
# sources for unique-mcp / unique-toolkit (which live outside this build
# context in the monorepo) so the image can be built standalone, e.g. with
# `az acr build` from this directory.
RUN uv lock --no-sources && \
    uv sync --frozen --no-install-project --no-dev

# Copy the application source code
COPY . .

# Install the project itself
RUN uv sync --frozen --no-dev

# -----------------------------------------------------------------------------
# Runtime stage
# -----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm@sha256:d50fb7611f86d04a3b0471b46d7557818d88983fc3136726336b2a4c657aa30b AS runtime

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
EXPOSE 8004

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8004/health')" || exit 1

# Run the application
CMD ["python", "-m", "mcp_space_chat.server"]
