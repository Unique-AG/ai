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
    pip install --no-cache-dir "uv==0.7.19"

# Copy only requirements to cache them in docker layer
WORKDIR /app

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

COPY requirements.txt pyproject.toml ./

# Project initialization (install dependencies)
RUN uv venv && uv pip install -r requirements.txt

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
