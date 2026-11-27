# Pinned by version and digest, same governed image the platform docker-base uses.
FROM python:3.12-slim-trixie@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir uv==0.13.7 && uv sync --no-dev

EXPOSE 8002
CMD ["uv", "run", "python", "src/mcp_sql_demo/mcp_sql_demo.py"]
