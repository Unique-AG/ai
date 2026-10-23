# =============================================================================
# Search Proxy - Container Image
#
# Build context must be the repository root so uv can resolve the full
# workspace (pyproject.toml + uv.lock + all workspace member sources).
#
# Both cd-containerize and ci-containerize set context: .
# =============================================================================
FROM ghcr.io/astral-sh/uv:0.13.5@sha256:32a7bb39b496babbd997b0a39a4d66c126bdaf5661b302bf6f06abda8deca6ff AS uv

# ── Stage 1: install deps into an isolated venv ───────────────────────────────
FROM python:3.12-slim-trixie@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704 AS builder

COPY --from=uv /uv /usr/bin/uv

# copy mode avoids hard-link failures across layers; compile bytecode at build time
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY . .

RUN uv sync --frozen --package unique-search-proxy --no-dev --no-editable

# ── Stage 2: lean runtime image ───────────────────────────────────────────────
FROM python:3.12-slim-trixie@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704 AS runtime

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# glibc caps malloc arenas at 8 per core of the node, not of the pod's CPU limit
ENV MALLOC_ARENA_MAX=2

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
