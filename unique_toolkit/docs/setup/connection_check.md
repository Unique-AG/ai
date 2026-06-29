# API Connection Check

> **Audience:** Developers integrating the toolkit who want to verify connectivity at startup or diagnose URL resolution issues.
> **Class:** `unique_toolkit.app.unique_settings`

---

## When to use what

| You have… | Call… |
|---|---|
| A fully configured `UniqueSettings` | `await settings.check_connection()` |
| Only a `UniqueApi` instance (e.g. in a test) | `await api.check_connection(user_id, company_id)` |

`UniqueSettings.check_connection` is the standard entry point. It handles SDK initialisation automatically. `UniqueApi.check_connection` is the lower-level primitive — useful when you need to probe a specific base URL without a full settings object.

---

## Full call flow

```mermaid
sequenceDiagram
    participant C as Caller
    participant S as UniqueSettings
    participant A as UniqueApi
    participant SDK as unique_sdk globals
    participant LLM as LLMModels.get_models_async

    C->>S: check_connection()
    S->>A: _probe_check_failed = False
    S->>SDK: init_sdk() → api_base = sdk_url()
    S->>A: check_connection(user_id, company_id)

    A->>LLM: get_models_async(user_id, company_id)

    alt Success — models returned
        LLM-->>A: {"models": [...]}
        A->>A: _probe_check_failed = False
        A-->>S: True (≥1 model) / False (0 models)
    else Exception — network / auth error
        LLM-->>A: raises
        A->>A: _probe_check_failed = True
        A-->>S: raises UniqueApiConnectionError
    end

    S->>SDK: init_sdk() [finally] → api_base = sdk_url()
    S-->>C: True / False / UniqueApiConnectionError
```

---

## `sdk_url()` fallback state machine

`UniqueApi` holds a private `_probe_check_failed` flag. It controls what `sdk_url()` returns, which in turn controls what `init_sdk()` writes to `unique_sdk.api_base`.

```mermaid
stateDiagram-v2
    [*] --> Computed : startup (_probe_check_failed = False)

    Computed --> Computed : check_connection succeeds\nsdk_url() = resolved path\n(e.g. /public/chat-gen2)

    Computed --> Fallback : check_connection raises\n_probe_check_failed = True\nsdk_url() = base_url

    Fallback --> Computed : next check_connection call\nresets flag → False\ninit_sdk re-resolves path

    note right of Fallback
        SDK calls use base_url directly.
        Works for single-tenant deployments
        where base_url IS the API root.
    end note
```

**Key invariant:** `UniqueSettings.check_connection` always resets `_probe_check_failed = False` *before* calling `init_sdk()`. This guarantees every retry probes the canonical computed URL rather than a stale fallback, so a transient failure does not permanently redirect the SDK to the wrong path.

---

## Return values and exceptions

| Outcome | `_probe_check_failed` | `sdk_url()` | Return / raise |
|---|---|---|---|
| ≥1 model returned | `False` | computed path | `True` |
| 0 models returned | `False` | computed path | `False` |
| Network / auth error | `True` | `base_url` | raises `UniqueApiConnectionError` |

`UniqueApiConnectionError` carries `.base_url` (the configured env value) so you can log exactly which URL was attempted.

---

## Typical usage

```python
from unique_toolkit.app.unique_settings import UniqueApiConnectionError, UniqueSettings

settings = UniqueSettings.from_env_auto_with_sdk_init()

try:
    connected = await settings.check_connection()
    if connected:
        print("API ready, models available")
    else:
        print("API reachable but no models configured")
except UniqueApiConnectionError as exc:
    print(f"Cannot reach API at {exc.base_url}: {exc}")
```
