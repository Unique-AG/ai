# =============================================================================
# Search Proxy - Container Image
#
# Build context must be the repository root so uv can resolve the full
# workspace (pyproject.toml + uv.lock + all workspace member sources).
#
# Both cd-containerize and ci-containerize set context: .
# =============================================================================
FROM ghcr.io/astral-sh/uv:0.12.0@sha256:606e70c71c852d03f611b1e56a195d08648507018a7057fab82c4974c4eae105 AS uv

# ── Stage 1: install deps into an isolated venv ───────────────────────────────
FROM python:3.14-slim-trixie@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6 AS builder

COPY --from=uv /uv /usr/bin/uv

# copy mode avoids hard-link failures across layers; compile bytecode at build time
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY . .

RUN uv sync --frozen --package unique-search-proxy --no-dev --no-editable

# ── Stage 2: lean runtime image ───────────────────────────────────────────────
FROM python:3.14-slim-trixie@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# uid 1000 is what the Helm chart pins as runAsUser
RUN useradd -m -u 1000 appuser

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY connectors/unique_search_proxy/unique_search_proxy_client/deploy/entrypoint.sh ./

RUN chown -R appuser:appuser /app && \
    chmod +x entrypoint.sh

USER appuser

EXPOSE 8080

ENTRYPOINT ["./entrypoint.sh"]
