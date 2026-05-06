# Track B — Azure + node-chat details

## Terraform (infrastructure repo)

Terraform lives in the **infrastructure** repo. Look for existing `azurerm_cognitive_deployment` resources for the same Azure OpenAI account and copy the pattern:

1. Add or update `azurerm_cognitive_deployment` resource(s) for the new model — one per deployment (e.g. base + chat variants). Key properties: `model.name`, `model.version`, `sku.capacity`.
2. Update the Key Vault secret holding endpoint definitions (commonly `azure-openai-endpoint-definitions`) so node-chat can discover the new deployment at startup.
3. If the model requires a new API key or endpoint, add a corresponding Key Vault secret reference.

**Tip:** search the infrastructure repo for an existing model deployment (e.g. `gpt-5.4`) to find the exact Terraform module and variable pattern to replicate.

## Node-chat registration — code examples

Three files in `next/services/node-chat/src/openai/`:

### 1. `language-model.enum.ts`

Add to `LanguageModel` enum and `LanguageModelNameKey`:

```typescript
// In LanguageModel enum:
AZURE_GPT_55_2026_0901 = 'AZURE_GPT_55_2026_0901',

// In LanguageModelNameKey:
AZURE_GPT_55_2026_0901: 'gpt-5.5-2026-09-01', // EU, US ✅
```

### 2. `azure-sdk-openai.service.factory.ts`

Add a `case` in the factory `switch` and add the model to `UNIQUEAI_SUPPORTED_MODELS`:

```typescript
// In UNIQUEAI_SUPPORTED_MODELS array:
LanguageModelNameKey.AZURE_GPT_55_2026_0901,

// In the factory switch:
case LanguageModel.AZURE_GPT_55_2026_0901:
  return new AzureSdkOpenAIService(
    enableV1,
    this.getConfigOfModel({
      modelKey: 'gpt-5.5-2026-09-01',
      maxToken: 1000000,
      apiVersion: '2024-10-21',
    }),
    this.azureSdkOpenAICommonService.getTokenCount,
    this.authTokenService,
    openAIClientOptions,
  );
```

### 3. `azure-sdk-openai.service.ts`

If the model needs special parameter handling (e.g. reasoning params), update the `getDeploymentName()` switch to map the `modelKey` to the Azure deployment name.

## Troubleshooting

| Symptom | Likely cause |
|---------|-------------|
| `reasoning_effort does not support null` | `default_options` in `LanguageModelInfo` uses Python `None` instead of string `"none"`. See [LESSONS-LEARNED.md](LESSONS-LEARNED.md). |
| Works in plain chat but fails in agentic space | Bug in the Python toolkit's parameter construction — check `responses_api.py` reasoning handling and the toolkit version pinned in `assistants-core`. |
| Works in agentic space but fails in plain chat | Bug in node-chat TypeScript Azure SDK service — check `azure-sdk-openai.service.ts` option spreading. |
| Model works on master but not on release branch | Cherry-pick was incomplete — check that `assistants-core` toolkit version was bumped alongside node-chat changes. |
