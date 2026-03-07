FROM python:3.12-slim
WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir uv && uv sync --no-dev --frozen

EXPOSE 8002
CMD ["uv", "run", "python", "src/mcp_sql_demo/mcp_sql_demo.py"]
