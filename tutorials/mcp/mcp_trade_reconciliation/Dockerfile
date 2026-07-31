# Pinned by version and digest for reproducible builds, same governed image the
# platform docker-base uses (python 3.12 on Debian trixie, linux/amd64).
FROM python:3.12-slim-trixie@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir uv==0.11.33 && uv sync --no-dev

EXPOSE 8003
CMD ["uv", "run", "python", "src/mcp_trade_reconciliation/mcp_trade_reconciliation.py"]
