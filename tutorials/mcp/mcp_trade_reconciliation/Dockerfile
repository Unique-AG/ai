# Pinned by version and digest for reproducible builds, same governed image the
# platform docker-base uses (python 3.12 on Debian trixie, linux/amd64).
FROM python:3.12-slim-trixie@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir uv==0.11.33 && uv sync --no-dev

EXPOSE 8003
CMD ["uv", "run", "python", "src/mcp_trade_reconciliation/mcp_trade_reconciliation.py"]
