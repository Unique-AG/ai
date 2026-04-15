# Track C — AI toolkit details

## LanguageModelInfo code example

In `unique_toolkit/unique_toolkit/language_model/infos.py`:

### 1. Enum entry

Convention:
- Azure models: `AZURE_GPT_54_2026_0305 = "AZURE_GPT_54_2026_0305"`
- LiteLLM models: `OPENAI_GPT_54 = "litellm:openai-gpt-5-4"`

### 2. `LanguageModelInfo.from_name()` case

```python
case LanguageModelName.OPENAI_GPT_54:
    return LanguageModelInfo(
        name=model_name,
        provider=LanguageModelProvider.LITELLM,
        version="2026-03-05",
        token_limits=LanguageModelTokenLimits(
            token_limit_input=200_000,
            token_limit_output=100_000,
        ),
        capabilities=[
            ModelCapabilities.FUNCTION_CALLING,
            ModelCapabilities.STREAMING,
        ],
        temperature_bounds=TemperatureBounds(
            min_temperature=0.0, max_temperature=1.0
        ),
        supported_reasoning_efforts=[
            "low", "medium", "high", "xhigh",
        ],
        default_options={"reasoning_effort": "medium"},
    )
```

## Field reference

| Field | Description |
|-------|-------------|
| `token_limits` | Input and output token limits — cite the model card |
| `capabilities` | `FUNCTION_CALLING`, `STREAMING`, `VISION`, etc. |
| `temperature_bounds` | Min/max temperature — reasoning models typically use `(0.0, 1.0)`. Never use `(1.0, 1.0)` — this was a past mistake that locked temperature to 1.0 regardless of reasoning state. |
| `supported_reasoning_efforts` | `None` = unknown (pass-through), `[]` = no reasoning, `["low", "medium", "high"]` = validated list |
| `default_options` | Default `reasoning_effort` and other defaults. **Critical: use the string `"none"` — never Python `None`.** See [LESSONS-LEARNED.md](LESSONS-LEARNED.md). |

## LANGUAGE_MODEL_INFOS env override (early exposure)

Before a toolkit release is published, you can expose a model immediately by setting the `LANGUAGE_MODEL_INFOS` environment variable on the relevant service. Useful for smoke-testing a model in QA before the toolkit PR is merged.

### Format

JSON dict where each key is a model identifier and each value is a `LanguageModelInfo`-compatible dict:

```bash
LANGUAGE_MODEL_INFOS='{"MY_NEW_MODEL": {"name": "litellm:my-new-model", "provider": "LITELLM", "version": "2026-01-01", "capabilities": ["function_calling", "streaming"], "token_limits": {"token_limit_input": 128000, "token_limit_output": 16384}}}'
```

### Where to set it

Set the env var in the service's app configuration or Helm values overlay for the target environment. The toolkit parses this at startup and merges it with the hardcoded model registry.

### Caveats

- This is a **temporary** measure — always follow up with a proper toolkit PR.
- Models loaded via env have `supported_reasoning_efforts=None` (unknown / pass-through) unless explicitly set in the JSON.
- If `default_options.reasoning_effort` is set but `supported_reasoning_efforts` is empty, the model's default effort will not be validated.
