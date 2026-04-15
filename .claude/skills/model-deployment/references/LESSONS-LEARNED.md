# Lessons learned

These come from real deployment experience and real incidents — refer back to them when something looks off.

## `default_options` pitfall: `None` vs `"none"` (caused production incident)

When defining `default_options` for a reasoning model, **never** use Python `None` for `reasoning_effort`:

```python
# BAD — caused reasoning_effort=null sent to Azure, which rejects it
default_options={"reasoning_effort": None}

# GOOD — explicit string value, accepted by Azure
default_options={"reasoning_effort": "none"}

# ALSO GOOD — omit the key entirely if no default is needed
default_options={}
```

**What happened:** `AZURE_GPT_51_2025_1113` was defined with `"reasoning_effort": None` in `default_options`. The toolkit's `_prepare_responses_params_util` checked `"reasoning_effort" in model_info.default_options` (key existence), found the key, and constructed `Reasoning(effort=None)`. This serialized to `reasoning_effort: null` in the Azure API request. Azure rejected it: *"reasoning_effort does not support null. Supported values are: none, low, medium, high."*

The guard only checked if the key was present, not whether the value was non-null. The fix (v1.57.0) added `resolve_temp_and_reasoning()` which explicitly substitutes `None` with the model's declared default.

## Dual code paths: node-chat vs assistants-core

Azure models are called through **two independent paths**:

1. **node-chat (TypeScript)** — Chat Completions and Responses API via the Azure SDK. Used by plain chat spaces.
2. **assistants-core (Python)** — Responses API via `unique_toolkit`. Used by agentic spaces with Python modules.

These paths have different handling for parameters like `reasoning_effort`. A bug in the toolkit Python path may not reproduce in node-chat, and vice versa. **Always test both paths** when deploying or updating a model: send a message in a plain chat space (node-chat) AND in an agentic assistant space (assistants-core).

## Cherry-pick completeness across repos

When cherry-picking model support into a release branch, **all cross-repo dependencies must be bumped together**. In a past incident, GPT-5.4 was cherry-picked into the release branch (node-chat TypeScript changes) but the `unique_toolkit` version bump in `assistants-core` was forgotten. This left the buggy toolkit version in place for gpt-5.1, causing the `reasoning_effort: null` production error.

Checklist for cherry-picks:
- [ ] Node-chat TypeScript changes (language-model enum, factory, service)
- [ ] `assistants-core` `pyproject.toml` toolkit version bump
- [ ] LiteLLM overlay changes (if applicable)
- [ ] Terraform changes (if applicable)

## Responses API is stricter than Chat Completions API

- The Responses API (used by the Python toolkit in `assistants-core`) sends parameters directly to Azure and rejects invalid values like `reasoning_effort: null`.
- The Chat Completions API (used by node-chat via the Azure SDK) may silently drop or ignore malformed optional parameters in some cases.
- This means a model definition bug can cause errors in agentic Python spaces but not in plain chat spaces. When investigating "model X works in chat but fails in assistants," look at the toolkit's parameter construction.

## Restart the right thing

- To reload config/secrets: roll the **Kubernetes Deployment**.
- Restarting an **HPA** does not reload running pods (it only adjusts autoscaling).

## Never guess model facts

- Token limits, capabilities, model identifiers: use authoritative sources only.
- If no source is available, ask the user to provide a link or confirm explicitly.
