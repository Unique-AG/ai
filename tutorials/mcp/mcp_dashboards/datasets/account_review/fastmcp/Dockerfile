# Build context is a staged directory prepared by deploy.sh (not the full monorepo).
FROM python:3.12-slim-trixie@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de
WORKDIR /app

COPY unique_mcp /deps/unique_mcp
COPY unique_toolkit /deps/unique_toolkit
COPY unique_sdk /deps/unique_sdk

COPY mcp_dashboards/helpers/python/pyproject.toml mcp_dashboards/helpers/python/README.md mcp_dashboards/helpers/python/uv.lock ./
COPY mcp_dashboards/helpers/python/src/ ./src/
COPY mcp_dashboards/datasets/account_review/fastmcp/data/account_review_dataset.xlsx ./dataset/data/
COPY mcp_dashboards/datasets/account_review/fastmcp/generated/ ./dataset/generated/
COPY mcp_dashboards/datasets/account_review/fastmcp/static/ ./dataset/static/
COPY mcp_dashboards/datasets/account_review/fastmcp/import_plan.py ./dataset/
COPY mcp_dashboards/datasets/account_review/fastmcp/admin_site.py ./dataset/
COPY mcp_dashboards/datasets/account_review/fastmcp/paths.py ./dataset/
COPY mcp_dashboards/datasets/account_review/fastmcp/constants.py ./dataset/
COPY mcp_dashboards/datasets/account_review/fastmcp/repository.py ./dataset/
COPY mcp_dashboards/datasets/account_review/fastmcp/runtime.py ./dataset/
COPY mcp_dashboards/datasets/account_review/fastmcp/domain.py ./dataset/
COPY mcp_dashboards/datasets/account_review/fastmcp/email_drafts.py ./dataset/
COPY mcp_dashboards/datasets/account_review/fastmcp/mcp_tools.py ./dataset/
COPY mcp_dashboards/datasets/account_review/fastmcp/app.py ./dataset/
COPY mcp_dashboards/datasets/account_review/fastmcp/server.py ./dataset/
COPY mcp_dashboards/datasets/account_review/fastmcp/scripts/docker_rewrite_sources.py /tmp/docker_rewrite_sources.py

RUN python /tmp/docker_rewrite_sources.py \
    && pip install --no-cache-dir uv==0.11.33 \
    && uv sync --no-dev

ENV UNIQUE_MCP_LOCAL_BASE_URL=http://0.0.0.0:8004
ENV EXCEL_PATH=/app/dataset/data/account_review_dataset.xlsx
ENV SQLITE_PATH=/app/dataset/data/account_review.sqlite

EXPOSE 8004
# Use the synced venv directly — `uv run` re-resolves and can pull dev deps at boot.
CMD ["/app/.venv/bin/python", "/app/dataset/app.py"]
