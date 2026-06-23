# Search Proxy — Helm chart autogeneration

The provider-facing parts of the `helm-chart/` are **generated from the Pydantic settings
classes**, not written by hand. The settings are the single source of truth: add a field to a
settings class, regenerate, and the `values.yaml` defaults, the env-injection template, the
egress rules, and the JSON schema all update together and stay consistent.

```
web/settings/providers/<provider>.py        ─┐
web/settings/client.py  (HttpClientSettings)  ├─ inputs (Pydantic + @helm_settings)
web/settings/monitoring.py (PrometheusSettings)┘
            │
            ▼  web/helm/registry.py  →  web/helm/generator/
            │   (scripts/generate_helm_config.py)
            ▼
helm-chart/values.yaml                     # @helm-gen:begin..end providers region
helm-chart/templates/_providers.tpl        # env injection + Cilium egress hooks
helm-chart/values.additional.schema.json   # provider JSON schema
```

> The three outputs above are **generated — do not hand-edit**. Everything else in
> `helm-chart/` (the `base` dependency, identity, probes, resources, …) is authored normally.

---

## 1. Inputs: what drives the generation

Each settings class that should appear in the chart is decorated with `@helm_settings`
(`web/helm/metadata.py`):

```python
@helm_settings(title="Google Search", helm_key="googleSearch")
@provider_credentials(_ENV_PREFIX)              # _ENV_PREFIX = "GOOGLE_SEARCH_"
class _GoogleCredentials(ProviderCredentials):
    api_key: LogSecretStr = Field(default=LogSecretStr(NOT_PROVIDED))
    api_endpoint: str = Field(default="https://www.googleapis.com/customsearch/v1")
    engine_id: str = Field(default=NOT_PROVIDED)
```

- **`helm_key`** → the top-level block name in `values.yaml` (`googleSearch:`). A class with
  `helm_key=None` (e.g. Prometheus, URL-safety) is tracked for the startup report but produces
  **no** chart block.
- **`title`** → human label in the generated schema description and startup logs.
- **`egress`** → drives the Cilium egress rule (see §4).
- **env prefix** (from `@provider_credentials` / `@helm_settings(env_prefix=…)`) → every env
  var name is `<PREFIX><FIELD_NAME_UPPER>`.

The registry (`web/helm/registry.py`) collects all decorated classes; the generator
(`web/helm/generator/`) introspects each one's Pydantic fields.

---

## 2. How a Python field maps to Helm

For each model field, `iter_helm_fields` (`web/helm/generator/introspect.py`) decides how it
renders. The field **type** and **default** are what matter:

| Python field | Schema (`connection.<name>`) | `values.yaml` | Template (`_providers.tpl`) |
| --- | --- | --- | --- |
| `LogSecretStr` / `SecretStr` | `valueSourceSensitive` | commented placeholder | `base.valueSource.env` (from a Secret) |
| `str` default `NOT_PROVIDED` | `valueSourceString`, **required when enabled** | commented placeholder | `required "…"` env value |
| `str` with URL default | `string` (`format: uri`) | the default value | plain `value:` |
| `str` / `Literal` | `valueSourceString` | the default | plain `value:` |
| `bool` / `int` / `float` | `valueSourceBoolean` / `Integer` / `number` | the default | plain `value:` |
| `list[str]` (default) | skipped (documented as a comment) | commented placeholder | skipped |
| `list[str]` + `helm: {overridable: true}` | `array` of `string` | the default rendered as a real list | plain `value:` JSON-encoded (`\| toJson`) |
| `dict`, or other non-scalar | skipped | skipped | skipped |

Rules of thumb baked into the generator:

- **Name**: `snake_case` field → `camelCase` Helm key (`engine_id` → `engineId`).
- **Sensitive** = the type is `SecretStr`/`LogSecretStr` (or `json_schema_extra={"helm": {"sensitive": true}}`).
- **Required-when-enabled** = the default is the `NOT_PROVIDED` sentinel (or
  `helm.required_when_enabled`). These get added to the schema's conditional `required` list
  *and* a `fail`/`required` guard in the template, so a provider enabled without its mandatory
  inputs fails `helm template` with a clear message.
- **Overridable lists**: a `list[str]` is documentation-only by default (its code default is the
  source of truth and isn't exposed to overlays). Mark it with
  `json_schema_extra={"helm": {"overridable": true}}` to expose it: the default renders as a real
  `values.yaml` list, the schema gets an `array` of `string`, and the template injects it as a
  single JSON-encoded env var that pydantic-settings parses back into a list. Overlays **replace**
  the whole list (Helm does not merge arrays), so a customer-managed tenant supplies the full set.
- A field can be hidden with `json_schema_extra={"helm": {"skip": true}}` or renamed/overridden
  via the same `helm` extra (`helm_name`, `value_source`).

---

## 3. How secrets flow end-to-end

Secrets are never plain text in the chart. Because secret fields are typed `LogSecretStr`,
the generator emits them as `valueSourceSensitive`, which the schema restricts to exactly two
shapes — `fromSecret` or `fromSecretProvider` (bare strings, `value:`, and `fromConfigMap:`
are rejected):

```
LogSecretStr field ─▶ schema: valueSourceSensitive ─▶ overlay sets fromSecret/fromSecretProvider
                   ─▶ _providers.tpl: base.valueSource.env ─▶ container env var ─▶ pydantic reads it
```

In your environment overlay you supply one of:

```yaml
# a) reference an existing Kubernetes Secret
googleSearch:
  enabled: true
  connection:
    engineId: my-cx-id                 # required, non-secret
    apiKey:
      fromSecret: { name: search-proxy-secrets, key: GOOGLE_SEARCH_API_KEY }

# b) pull from Azure Key Vault (declare the vault once under top-level secretProvider)
secretProvider:
  tenantId: <tenant>
  userAssignedIdentityID: <uami>
  vaults:
    my-keyvault: { GOOGLE_SEARCH_API_KEY: google-search-api-key }
googleSearch:
  connection:
    apiKey:
      fromSecretProvider: { vault: my-keyvault, secretKey: GOOGLE_SEARCH_API_KEY }
```

The generated `values.yaml` only leaves a commented placeholder for each secret
(`# apiKey: <fromSecret or fromSecretProvider>`); the real wiring lives in the per-cluster
overlay, never in this chart.

Secret fields by block (all rendered as `valueSourceSensitive`):

| Block | Secret field → env var |
| --- | --- |
| `googleSearch` / `braveSearch` / `perplexitySearch` / `tavily` / `jina` / `firecrawl` | `apiKey` → `<PREFIX>API_KEY` |
| `vertexaiAgent` | `serviceAccountCredentials` → `VERTEXAI_AGENT_SERVICE_ACCOUNT_CREDENTIALS` (optional) |
| `httpClient` | `proxyUsername` / `proxyPassword` → `HTTP_CLIENT_PROXY_USERNAME` / `…PASSWORD` |

(`bingAgent` has no `SecretStr` field; its `endpoint` and `bingResourceConnectionString` are
required plain values injected from the overlay.)

For **local development** there is no chart — settings load from environment variables / a
`.env` in the working directory (see `web/settings/base.py`). `deploy/.env` is the annotated
template listing every variable; it is gitignored, so never commit real keys.

---

## 4. Egress is generated too

Each provider's outbound Cilium rule is derived from the `egress` argument on `@helm_settings`
and rendered into `_providers.tpl` (only when `networkPolicy.enabled`):

- **endpoint field** (default) → the generator parses the configured endpoint URL at render
  time and emits `toFQDNs: matchName: <host>` on the URL's port (443/`http`→80/explicit).
- **domain wildcard** (e.g. Jina, `EgressDomainWildcard("api_domain")`) → emits
  `toFQDNs: matchPattern: "*.<domain>"`, covering its multiple derived subdomains.
- **`egress=None`** (e.g. agent providers reaching Azure/GCP) → no rule generated.

---

## 5. Regenerating the chart

Run from the **client root** (`unique_search_proxy_client/`):

```bash
# 1. Regenerate values.yaml (providers region), _providers.tpl, values.additional.schema.json
uv run python scripts/generate_helm_config.py

# 2. Re-merge the full values.schema.json from the shared base chart
#    (run from the ai repo root — step 1 deliberately does NOT do this)
( cd ../../.. && scripts/render-values-schema.sh )

# 3. Render every fixture to confirm the chart still templates
#    (needs helm + login to ghcr.io for the base dependency)
scripts/render_helm_fixtures.sh
```

Drift check for CI / pre-commit (exit 1 if committed artifacts are stale):

```bash
uv run python scripts/generate_helm_config.py --check
```

### Adding or changing a provider field

1. Edit the settings class in `web/settings/providers/<provider>.py` (or `client.py` /
   `monitoring.py`). Type + default determine sensitivity, required-ness, and schema type;
   `@helm_settings` metadata controls the block name, title, and egress.
2. Run steps 1–3 above and review the diff in `values.yaml`, `_providers.tpl`, and the schemas.
3. For a brand-new provider, also add `helm-chart/fixtures/values-<provider>-enabled.yaml`
   so the render test exercises it.
