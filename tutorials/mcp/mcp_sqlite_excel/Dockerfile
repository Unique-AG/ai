FROM python:3.12-slim
WORKDIR /app

COPY pyproject.toml README.md uv.lock ./
COPY src/ ./src/
COPY data/ ./data/

RUN pip install --no-cache-dir uv \
    && uv sync --no-dev --frozen \
    && uv run generate-sample-excel

ENV HOST=0.0.0.0
ENV PORT=8004
ENV EXCEL_PATH=/app/data/sample_portfolio.xlsx
ENV SQLITE_PATH=/app/data/portfolio.db

EXPOSE 8004
CMD ["uv", "run", "mcp-sqlite-excel"]
