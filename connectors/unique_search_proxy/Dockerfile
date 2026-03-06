# =============================================================================
# Search Proxy - Experimental Image
# =============================================================================
FROM python:3.12-slim-bookworm

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    UV_NO_PROGRESS=1

# Create user and install uv
RUN useradd -m appuser && \
    pip install --no-cache-dir "uv>=0.7.19,<0.8"

# Copy only requirements to cache them in docker layer
WORKDIR /app
COPY uv.lock pyproject.toml ./

# Project initialization (install dependencies)
RUN uv sync --locked --no-dev --no-install-project

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY web/ ./

# Set ownership and permissions
RUN chown -R appuser:appuser /app && \
    chmod +x entrypoint.sh

USER appuser

# Expose port
EXPOSE 8080

# Entrypoint script handles startup
ENTRYPOINT ["./entrypoint.sh"]
