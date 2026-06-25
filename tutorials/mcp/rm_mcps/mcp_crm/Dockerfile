FROM python:3.12-slim
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir uv && uv sync --no-dev

EXPOSE 8004
CMD ["uv", "run", "python", "src/mcp_crm/mcp_crm.py"]
