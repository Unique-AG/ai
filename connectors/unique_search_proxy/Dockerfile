# =============================================================================
# Search Proxy - Experimental Image
# =============================================================================
FROM python:3.12-slim-bookworm

ARG POETRY_VERSION=2.0.1

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    # Poetry's configuration:
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_CACHE_DIR='/var/cache/pypoetry' \
    POETRY_HOME='/usr/local'

# Create user and install Poetry
RUN useradd -m appuser && \
    pip install --no-cache-dir "poetry==${POETRY_VERSION}"

# Copy only requirements to cache them in docker layer
WORKDIR /app
COPY poetry.lock pyproject.toml ./

# Project initialization (install dependencies)
RUN poetry install --only=main --no-root --no-interaction --no-ansi

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
