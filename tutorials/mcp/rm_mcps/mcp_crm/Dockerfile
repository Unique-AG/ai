# Pinned by digest for reproducible, supply-chain-safe builds (python:3.12-slim, linux/amd64).
FROM python:3.12-slim@sha256:d764629ce0ddd8c71fd371e9901efb324a95789d2315a47db7e4d27e78f1b0e9
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir uv==0.11.3 && uv sync --no-dev

EXPOSE 8004
CMD ["uv", "run", "python", "src/mcp_crm/mcp_crm.py"]
