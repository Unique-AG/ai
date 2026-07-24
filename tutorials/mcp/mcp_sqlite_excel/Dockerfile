# Build context is a staged directory prepared by deploy.sh (not the full monorepo).
FROM python:3.12-slim
WORKDIR /app

COPY unique_mcp /deps/unique_mcp
COPY unique_toolkit /deps/unique_toolkit
COPY unique_sdk /deps/unique_sdk

COPY mcp_sqlite_excel/pyproject.toml mcp_sqlite_excel/README.md ./
COPY mcp_sqlite_excel/src/ ./src/
COPY mcp_sqlite_excel/data/ ./data/
COPY mcp_sqlite_excel/scripts/docker_rewrite_sources.py /tmp/docker_rewrite_sources.py

RUN python /tmp/docker_rewrite_sources.py \
    && pip install --no-cache-dir uv \
    && uv sync --no-dev \
    && uv run generate-sample-excel

ENV UNIQUE_MCP_LOCAL_BASE_URL=http://0.0.0.0:8004
ENV EXCEL_PATH=/app/data/account_review_dataset.xlsx
ENV SQLITE_PATH=/app/data/portfolio.db

EXPOSE 8004
CMD ["uv", "run", "mcp-sqlite-excel"]
