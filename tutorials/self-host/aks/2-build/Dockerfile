# ============================================================================
# MOCK FILE - SDK DEPLOYMENT EXAMPLE
# ============================================================================
# This is a mock Dockerfile for demonstration purposes only. It shows how a
# containerized SDK assistant might be built. This file is NOT production-ready
# and should be adapted to your specific application requirements and security
# policies.
# ============================================================================

FROM python:3.12-slim-bookworm

ARG POETRY_VERSION=1.7.1

ENV PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_HOME='/usr/local' \
    APP_NAME='app' \
    PORT='8080'

RUN useradd -m app && \
    apt-get update && \
    apt-get install --no-install-recommends -y pipx curl && \
    PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/usr/local/bin pipx install poetry==${POETRY_VERSION} && \
    apt-get purge -y --auto-remove && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /code
COPY poetry.lock pyproject.toml /code/

RUN poetry env use /usr/local/bin/python3.12 && \
    poetry install --only=main --no-interaction

COPY . /code

RUN chown -R app:app /code && \
    chmod +x /code/entrypoint.sh

USER app

ENTRYPOINT ["/code/entrypoint.sh"]
