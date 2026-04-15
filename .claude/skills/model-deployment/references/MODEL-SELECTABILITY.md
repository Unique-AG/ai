# Model selectability

There are **two gatekeeping layers** that control whether a model is available and selectable on uniqueai.

## Layer 1: `UNIQUEAI_SUPPORTED_MODELS` (hardcoded in code)

This is a hardcoded array in `azure-sdk-openai.service.factory.ts` that defines which models are **available on the cluster**. If a model is not in this list, it cannot be used at all — even if it has an enum entry and factory case.

```typescript
export const UNIQUEAI_SUPPORTED_MODELS = [
  LanguageModelNameKey.AZURE_GPT_4o_2024_1120,
  LanguageModelNameKey.AZURE_GPT_54_2026_0305,
  'litellm:gemini-2-5-pro',
  // ... add your new model here
] as const;
```

You **must** add your model to this array (done in B3) for it to be cluster-available.

## Layer 2: `UNIQUEAI_ALLOWED_MODELS` (env var, per-company)

This environment variable on node-chat controls which of the cluster-available models are **selectable by end users** in the UI model picker. If a model should not appear in the user-facing dropdown, do not add it here.

- **Env var:** `UNIQUEAI_ALLOWED_MODELS` in the node-chat Helm chart / deployment config.
- **Format:** `companyId:MODEL_NAME,MODEL_NAME2;companyId2:MODEL_NAME3` — semicolon-separated company entries, colon-separated company ID and comma-separated model names.
- **Wildcard:** `*:MODEL_NAME` makes a model selectable for all companies.
- **Unset / empty:** when the env var is unset, the default model selection logic applies (all cluster models are available).

## Decision matrix

| Want the model to... | `UNIQUEAI_SUPPORTED_MODELS` | `UNIQUEAI_ALLOWED_MODELS` |
|---|---|---|
| Be available and selectable by users | Add | Add |
| Be available but only for internal/orchestrator use | Add | Do **not** add |
| Not be available at all | Do **not** add | N/A |

## Where to configure `UNIQUEAI_ALLOWED_MODELS`

- **Per-environment overlays:** `next/services/node-chat/deploy/<Env>/values.yaml` — production example at `next/services/node-chat/deploy/Prod/values.yaml`.
- **Helm chart default:** `next/services/node-chat/deploy/helm-chart/values.yaml` has the env var commented out by default.
- **Code:** parsed by `OpenAiconfigSchema` in `next/services/node-chat/src/openai/config-schema.ts`, used by the Azure SDK service factory to filter available models per company.

## Important notes

- The model names in `UNIQUEAI_ALLOWED_MODELS` must match the `LanguageModel` enum values (e.g. `AZURE_GPT_4o_2024_1120`), **not** the Azure deployment name or the LiteLLM `model_name`.
- If a model is listed in `UNIQUEAI_ALLOWED_MODELS` but is not in `UNIQUEAI_SUPPORTED_MODELS` or not deployed on the cluster, node-chat logs a warning: *"Model X is listed in UNIQUEAI_ALLOWED_MODELS but not found in the cluster list of models"*.
