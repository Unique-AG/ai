# Pinned by version and digest, same governed image the platform docker-base uses.
FROM python:3.12-slim-trixie@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir uv==0.11.33 && uv sync --no-dev

EXPOSE 8002
CMD ["uv", "run", "python", "src/mcp_sql_demo/mcp_sql_demo.py"]
