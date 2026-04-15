# Track A — LiteLLM config details

## Config entry examples

From our actual ArgoCD overlays:

```yaml
# Standard model
- model_name: anthropic-claude-opus-4-6
  litellm_params:
    model: anthropic/claude-opus-4-6
    api_key: os.environ/ANTHROPIC_API_KEY
    max_tokens: 20000

# Gemini model
- model_name: gemini-2-5-flash
  litellm_params:
    model: gemini/gemini-2.5-flash
    api_key: os.environ/GEMINI_API_KEY

# Model with thinking/reasoning enabled
- model_name: anthropic-claude-3-7-sonnet-thinking
  litellm_params:
    model: anthropic/claude-3-7-sonnet-20250219
    api_key: os.environ/ANTHROPIC_API_KEY
    temperature: 1.0
    max_tokens: 64000
    thinking:
      type: enabled
      budget_tokens: 20000
    additional_drop_params: ["top_p"]
```

### Notes

- `api_key` uses `os.environ/<KEY_NAME>` syntax — LiteLLM resolves this at runtime from pod environment.
- `max_tokens` is the **output** token limit for the proxy; set it conservatively to avoid exceeding context limits.
- For thinking/reasoning models, set `temperature: 1.0` (required by the provider) and configure the `thinking` block.

## Provider prefix conventions

- Gemini API key auth: `gemini/<model>` with `GEMINI_API_KEY`
- Anthropic: `anthropic/<model>` with `ANTHROPIC_API_KEY`
- OpenAI via LiteLLM: `openai/<model>` with `OPENAI_API_KEY`
- If the LiteLLM registry shows a different prefix for a new provider, confirm with the team first.

## model_name vs litellm_params.model

- `model_name` = user-facing key (no provider prefix): `gemini-2-5-flash`
- `litellm_params.model` = provider model string (with prefix): `gemini/gemini-2.5-flash`
- Common mistake: putting a provider string as `model_name`. If `model_name` contains `/`, it is almost certainly wrong.

## Preview naming

If the upstream model uses `-preview` in its name, keep `-preview` in the exposed `model_name` too.

## Troubleshooting

| Symptom | Likely cause |
|---------|-------------|
| Model not visible in LiteLLM UI | ArgoCD app not synced, Deployment not rolled, or YAML syntax error |
| "Model not available on cluster" | Config not applied, pods running old config, or model name mismatch |
| Wrong responses / unexpected model | Wrong provider prefix (e.g. missing `gemini/` prefix with `GEMINI_API_KEY`) |

## ArgoCD vs LiteLLM dashboard

- **ArgoCD** is the source of truth for config sync ("sync from git" happens here).
- **LiteLLM dashboard** is for inspecting proxy state (model list, logs) — you cannot deploy or sync from it.
