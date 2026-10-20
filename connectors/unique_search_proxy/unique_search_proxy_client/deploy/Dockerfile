# =============================================================================
# Search Proxy - Container Image
#
# Build context must be the repository root so uv can resolve the full
# workspace (pyproject.toml + uv.lock + all workspace member sources).
#
# Both cd-containerize and ci-containerize set context: .
# =============================================================================
FROM ghcr.io/astral-sh/uv:0.13.3@sha256:bee0a2a458fd956c5df7b8b4c5fed2257b0af34866e3da7b51db0be3acb375d1 AS uv

# ── Stage 1: install deps into an isolated venv ───────────────────────────────
FROM python:3.14-slim-trixie@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170 AS builder

COPY --from=uv /uv /usr/bin/uv

# copy mode avoids hard-link failures across layers; compile bytecode at build time
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY . .

RUN uv sync --frozen --package unique-search-proxy --no-dev --no-editable

# ── Stage 2: lean runtime image ───────────────────────────────────────────────
FROM python:3.14-slim-trixie@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170 AS runtime

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
