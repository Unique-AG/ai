# =============================================================================
# Search Proxy - Container Image
#
# Build context must be the repository root so uv can resolve the full
# workspace (pyproject.toml + uv.lock + all workspace member sources).
#
# Both cd-containerize and ci-containerize set context: .
# =============================================================================
FROM ghcr.io/astral-sh/uv:0.11.33@sha256:77280f2f771df71f90786c314fe1bbc1e023feac652969bbf139c280babf2eb7 AS uv

# ── Stage 1: install deps into an isolated venv ───────────────────────────────
FROM python:3.12-slim-trixie@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de AS builder

COPY --from=uv /uv /usr/bin/uv

# copy mode avoids hard-link failures across layers; compile bytecode at build time
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY . .

RUN uv sync --frozen --package unique-search-proxy --no-dev --no-editable

# ── Stage 2: lean runtime image ───────────────────────────────────────────────
FROM python:3.12-slim-trixie@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de

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
