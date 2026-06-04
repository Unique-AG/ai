# =============================================================================
# Search Proxy - Container Image
#
# Install modes (exactly one path must be used):
#   PACKAGE_VERSION     – PyPI install with hash-pinned requirements.txt (CD)
#   LOCAL_WHEEL_CORE + LOCAL_WHEEL_CLIENT – CI/local multi-package workspace wheels
#   LOCAL_WHEEL         – single pre-built .whl (legacy local builds)
# =============================================================================
FROM python:3.12-slim-bookworm@sha256:31c0807da611e2e377a2e9b566ad4eb038ac5a5838cbbbe6f2262259b5dc77a0

ARG PACKAGE_VERSION=""
ARG LOCAL_WHEEL=""
ARG LOCAL_WHEEL_CORE=""
ARG LOCAL_WHEEL_CLIENT=""

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

RUN useradd -m appuser

WORKDIR /app

COPY entrypoint.sh requirements.tx[t] ${LOCAL_WHEEL:+$LOCAL_WHEEL} ${LOCAL_WHEEL_CORE:+$LOCAL_WHEEL_CORE} ${LOCAL_WHEEL_CLIENT:+$LOCAL_WHEEL_CLIENT} ./

RUN if [ -n "$LOCAL_WHEEL_CLIENT" ]; then \
      if [ -n "$LOCAL_WHEEL_CORE" ]; then pip install --no-cache-dir "./$LOCAL_WHEEL_CORE"; fi; \
      pip install --no-cache-dir "./$LOCAL_WHEEL_CLIENT"; \
      rm -f "./$LOCAL_WHEEL_CORE" "./$LOCAL_WHEEL_CLIENT"; \
    elif [ -n "$LOCAL_WHEEL" ]; then \
      pip install --no-cache-dir "./$LOCAL_WHEEL" && rm -f "./$LOCAL_WHEEL"; \
    elif [ -n "$PACKAGE_VERSION" ]; then \
      pip install --no-cache-dir --require-hashes -r ./requirements.txt \
        && pip install --no-cache-dir --no-deps "unique-search-proxy==${PACKAGE_VERSION}" \
        && rm -f ./requirements.txt; \
    else \
      echo "ERROR: set PACKAGE_VERSION, LOCAL_WHEEL, or LOCAL_WHEEL_CORE+LOCAL_WHEEL_CLIENT" >&2; exit 1; \
    fi

RUN chown -R appuser:appuser /app && \
    chmod +x entrypoint.sh

USER appuser

EXPOSE 8080

ENTRYPOINT ["./entrypoint.sh"]
