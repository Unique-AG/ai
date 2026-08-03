# Pinned by version and digest, same governed image the platform docker-base uses.
FROM python:3.14-slim-trixie@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir uv==0.11.33 && uv sync --no-dev

EXPOSE 8002
CMD ["uv", "run", "python", "src/mcp_sql_demo/mcp_sql_demo.py"]
