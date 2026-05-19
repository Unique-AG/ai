# `feature_flags` — Python feature flag client

Remote feature flag evaluation backed by configuration-backend's GraphQL API,
with in-process TTL caching and graceful env-var fallback.

Mirrors the OpenFeature `evaluate` / `isEnabled` semantics used by the
Node.js `@unique/feature-flags` package. The OpenFeature Python SDK is
deliberately **not** used as a dependency — the interface is implemented
directly to avoid SDK overhead.

---

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `CONFIGURATION_BACKEND_URL` | No | `None` | Base URL of configuration-backend (e.g. `https://<your-configuration-backend>`). When absent, all evaluations use env-var fallback immediately. |
| `FEATURE_FLAG_SERVICE_ID` | **Yes** | — | Service identifier sent as `x-service-id`. Must match a value in configuration-backend's `Service` enum (e.g. `agentic-ingestion`). |
| `FEATURE_FLAG_CACHE_TTL_MS` | No | `30000` | In-process cache TTL in milliseconds. |

---

## `flag` argument convention

The `flag` argument to `evaluate()` / `is_enabled()` must be the
**upper-snake env-var-style key**, e.g.:

```
FEATURE_FLAG_ENABLE_PDF_CONTENT_EXTRACTION
FEATURE_FLAG_ENABLE_AGENTIC_METADATA_EXTRACTION_UN_15619
FEATURE_FLAG_ENABLE_IMAGE_CONTENT_EXTRACTION_UN_17223
```

This matches both the configuration-backend registry key convention and the
existing env-var names in Python services, so the env-var fallback path
requires no transformation.

---

## Usage

### Constructor injection (recommended for testing)

```python
from unique_toolkit.experimental.components.feature_flags import FeatureFlagClient

client = FeatureFlagClient(
    url="https://<your-configuration-backend>",
    service_id="agentic-ingestion",
    ttl_ms=30_000,
)

result = await client.evaluate(
    "FEATURE_FLAG_ENABLE_PDF_CONTENT_EXTRACTION",
    company_id=company_id,
    user_id=user_id,
)
# result.value  → bool
# result.reason → "remote" | "cached" | "fallback" | "default"

enabled = await client.is_enabled(
    "FEATURE_FLAG_ENABLE_PDF_CONTENT_EXTRACTION",
    company_id=company_id,
    user_id=user_id,
)
```

### `from_settings()` factory (reads env vars)

```python
client = FeatureFlagClient.from_settings()
```

### Singleton pattern (recommended for services)

```python
from functools import lru_cache

@lru_cache
def get_feature_flag_client() -> FeatureFlagClient:
    return FeatureFlagClient.from_settings()
```

---

## `FlagEvaluation.reason` values

| Value | Meaning |
|---|---|
| `"remote"` | Value was freshly fetched from configuration-backend. |
| `"cached"` | Value was returned from the in-process TTL cache. |
| `"fallback"` | Transport error or client unavailable; env-var default used. |
| `"default"` | Reserved for future use (e.g. flag key not registered). |

---

## Adopting in another Python service

1. Install the optional dep group: `uv add unique-toolkit[feature_flags]`
2. Set env vars: `CONFIGURATION_BACKEND_URL`, `FEATURE_FLAG_SERVICE_ID`
3. Add the service ID to configuration-backend's `Service` enum (`tyk-auth`)
   and to the `@AllowAccess` whitelist on the `evaluateFlag` resolver.
4. Register any new flag keys in `feature-flag.registry.ts`.
5. Replace `os.getenv("FEATURE_FLAG_*", "false")` call sites with
   `await client.is_enabled("FEATURE_FLAG_*", company_id=..., user_id=...)`.
