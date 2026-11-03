# Track B — Azure + node-chat details

## Terraform (infrastructure repo)

Terraform lives in the **infrastructure** repo. Look for existing `azurerm_cognitive_deployment` resources for the same Azure OpenAI account and copy the pattern:

1. Add or update `azurerm_cognitive_deployment` resource(s) for the new model — one per deployment (e.g. base + chat variants). Key properties: `model.name`, `model.version`, `sku.capacity`.
2. Update the Key Vault secret holding endpoint definitions (commonly `azure-openai-endpoint-definitions`) so node-chat can discover the new deployment at startup.
3. If the model requires a new API key or endpoint, add a corresponding Key Vault secret reference.

**Tip:** search the infrastructure repo for an existing model deployment (e.g. `gpt-5.4`) to find the exact Terraform module and variable pattern to replicate.

## Azure quota (`sku_capacity`)

`sku_capacity` is the deployment's share of a live Azure quota bucket. The bucket is **subscription + region + SKU** (`GlobalStandard` or `DataZoneStandard`). Two rows in the same subscription and the same region draw from one limit, even when they live in different tenant files. unique dev and unique qa/lz are that case: both Sweden Central, subscription `fb8bce09`.

Set each row to `min(requested capacity, remaining quota)`. If several new deployments share a bucket, their capacities must **sum** to no more than the limit. Split the way the sibling model already does when the bucket is shared (GPT-6.1 Sol is 7500/7500 on dev and qa against a 15000 Global Standard limit).

1. Region is the `oai_deployments_<region>` key the row sits under.
2. Subscription id is that workspace's Terraform `subscription_id` (Atlantis workspace / tfvars).
3. Read the live limit before writing the number. `currentValue` is what is already deployed; remaining is `limit - currentValue`. A new model is often `currentValue = 0`, so the row can use the full limit.

```bash
az cognitiveservices usage list --location <region> \
  --subscription <subscription-id> \
  --query "[?contains(name.value,'<model-name>')].{quota:name.value,used:currentValue,limit:limit}"
```

GPT-6.1 Terra (checked 2026-11-03) asked for 15000 Global Standard and 5000 Data Zone Standard. Live limits forced these clamps: us01 Global Standard 10000; skyline, sparkles, teapot, ch01, and tree/evx Data Zone Standard 3333; dev and qa 7500 each because they share one 15000 bucket. Rows already inside the limit stayed at the request. If a subscription is not available from the repo, say so in the PR and do not invent its capacity.

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
