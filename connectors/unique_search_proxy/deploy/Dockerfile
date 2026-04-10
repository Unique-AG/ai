# =============================================================================
# Search Proxy - Container Image
#
# Two install modes (exactly one must be set):
#   PACKAGE_VERSION  – install from PyPI:  pip install unique-search-proxy==<ver>
#   LOCAL_WHEEL      – install a pre-built .whl from the build context
#
# CI uses PACKAGE_VERSION after publishing to PyPI.
# Customers who prefer not to publish can build the wheel locally:
#   uv build --wheel --out-dir deploy/  (from the package root)
#   docker build \
#     --build-arg LOCAL_WHEEL=unique_search_proxy-0.2.0-py3-none-any.whl \
#     -t search-proxy deploy/
# =============================================================================
FROM python:3.12-slim-bookworm@sha256:31c0807da611e2e377a2e9b566ad4eb038ac5a5838cbbbe6f2262259b5dc77a0

ARG PACKAGE_VERSION=""
ARG LOCAL_WHEEL=""

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

RUN useradd -m appuser

WORKDIR /app

COPY entrypoint.sh ${LOCAL_WHEEL:+$LOCAL_WHEEL} ./

RUN if [ -n "$LOCAL_WHEEL" ]; then \
      pip install --no-cache-dir "./$LOCAL_WHEEL" && rm -f "./$LOCAL_WHEEL"; \
    elif [ -n "$PACKAGE_VERSION" ]; then \
      pip install --no-cache-dir "unique-search-proxy==${PACKAGE_VERSION}"; \
    else \
      echo "ERROR: set either PACKAGE_VERSION or LOCAL_WHEEL" >&2; exit 1; \
    fi

RUN chown -R appuser:appuser /app && \
    chmod +x entrypoint.sh

USER appuser

EXPOSE 8080

ENTRYPOINT ["./entrypoint.sh"]
