FROM python:3.12-slim-trixie@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN pip install --no-cache-dir uv==0.11.33 && uv sync --no-dev --frozen
COPY server.py .
COPY data/ data/
EXPOSE 8002
ENV PORT=8002
CMD ["uv", "run", "server.py"]
