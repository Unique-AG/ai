FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN pip install --no-cache-dir uv && uv sync --no-dev --frozen
COPY server.py .
COPY data/ data/
EXPOSE 8002
ENV PORT=8002
CMD ["uv", "run", "server.py"]
