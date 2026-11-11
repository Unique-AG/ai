FROM python:3.12-slim-trixie@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN pip install --no-cache-dir uv==0.11.33 && uv sync --no-dev --frozen
COPY server.py .
COPY data/ data/
EXPOSE 8002
ENV PORT=8002
CMD ["uv", "run", "server.py"]
