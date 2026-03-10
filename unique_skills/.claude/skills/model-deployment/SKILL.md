---
name: model-deployment
description: Deploy a new LLM model via LiteLLM (GitOps) and/or Azure (Terraform + node backend). Use when rolling out a new model to Dev/QA/Prod; always consult the user when unsure and cite sources for parameters (token window, model ids).
license: MIT
compatibility: claude cursor opencode
metadata:
  version: "1.0.0"
  languages: all
  audience: developers operators
  workflow: operations
  since: "2026-03-09"
---

# Model deployment (LLM — LiteLLM and/or Azure)

This skill consolidates how we deploy new LLM models across **monorepo** (LiteLLM overlays, node-chat, Terraform) and **ai repo** (toolkit model registry). Use it when assisting or performing a model rollout (e.g. GPT-5.4 via Azure to Dev/QA).

**Canonical sources:** The steps below are derived from:
- **ops-agent runbook:** `ops-agent/tasks/llm_model_deployment/HUMAN_RUNBOOK.md`
- **Agent contract:** `ops-agent/tasks/llm_model_deployment/agent_instructions.md`
- **Lessons learned:** `ops-agent/tasks/llm_model_deployment/LESSONS_LEARNED.md`

When you suggest deployment parameters (token limits, model ids, API versions), **always cite where you found them** (e.g. link to model card, LiteLLM registry, or the Jira ticket/PR that defined them). If you cannot find an authoritative source, **ask the user** — do not guess.

---

## When to use this skill

- Deploying a new model to Dev, QA, UAT, or Prod.
- Adding a model to LiteLLM proxy and/or Azure OpenAI.
- Adding a model to the ai toolkit language model registry.
- Troubleshooting “model not available on cluster” or config sync issues.

---

## Before you start: consult the user

Confirm with the user (do not assume):

- **Track:** `azure` | `litellm` | `both`
- **Environments** and **rollout order** (e.g. qa → uat → prod; or dev/qa only, not prod)
- **Model identifiers:** For LiteLLM: user-facing `model_name` and provider model string. For Azure: model name, version, deployment names, API version, capacity.
- **Token limits / capabilities:** If not in a cited source (model card, PR, ticket), ask the user to confirm or provide a link.
- **Toolkit:** Is the model already in the ai repo (merged or PR)? If not, should we add it in this rollout?

**Rule:** Do **not** invent token limits, provider strings, or capabilities. If you can’t find a reliable source, ask for confirmation or a link.

---

## Repo and file map

| Repo      | What you touch |
|-----------|----------------|
| **monorepo** | LiteLLM: `gitops-resources/argocd/clusters/<cluster>/<env>/value-overlays/litellm.yaml`. Node-chat: language-model enum, Azure factory config. Terraform: `azurerm_cognitive_deployment`, Key Vault secret (e.g. `azure-openai-endpoint-definitions`). |
| **ai**    | Toolkit: language model enum + `LanguageModelInfo` + tests (only if not already done). |

---

## Track A — LiteLLM (GitOps)

### A1) Validate model id and provider prefix

1. Use **LiteLLM model registry:** [https://models.litellm.ai/](https://models.litellm.ai/) — search for the model.
2. Confirm **provider prefix** (e.g. we use `gemini/...` with `GEMINI_API_KEY`).
3. Decide and document:
   - **User-facing key** (`model_name` in overlays): e.g. `gemini-3-flash-preview` (no provider prefix).
   - **Provider model** (`litellm_params.model`): e.g. `gemini/gemini-3-flash-preview`.
4. **Cite the source** (LiteLLM registry URL or model card) when you write these into config or PR description.

### A2) Update ArgoCD overlay(s)

1. Edit the relevant overlay(s), e.g.:
   - `monorepo/gitops-resources/argocd/clusters/unique/qa/value-overlays/litellm.yaml`
2. Add under `proxy_config.model_list`: `model_name`, `litellm_params.model`, `api_key` (e.g. `os.environ/<KEY_NAME>`).
3. Keep naming consistent with existing entries.

### A3) Monorepo PR

- Branch: `feat/litellm-<model-name>`
- Commit: `feat(litellm): add <model_name> model to <envs>`
- In the PR body: list which env overlays changed, user-facing model name and provider string, and **link to the source** you used for model id/token limits if relevant (e.g. Jira ticket, model card, previous deployment PR).

### A4) After merge: sync + restart

1. In **ArgoCD**, sync the LiteLLM app for the target env (Synced / Healthy).
2. **Roll the LiteLLM Deployment** (not the HPA) so pods reload config/secrets.
3. **Important:** Restarting the HPA does **not** reload pods; only rolling the Deployment does.

### A5) Verify

- LiteLLM dashboard: model in configured list.
- Smoke test with the exact id users will request (e.g. `litellm:<model_name>`).

### A6) Troubleshooting (LiteLLM)

- Model not visible → Argo not synced, or Deployment not rolled, or YAML error.
- “Model not available on cluster” → config not applied, or wrong `model_name` / provider string; restart the **correct Deployment**.

---

## Track B — Azure (Terraform + node backend)

### B1) Azure deployment details

Confirm with the user or from a **cited** source (ticket, internal doc, previous PR):

- Azure OpenAI resource/region, model name + version, deployment names (e.g. base/chat), capacity, RAI policy.
- **Cite:** Jira ticket or PR where these were decided (e.g. “Per UN-17948 and deployment PR #19819…”).

### B2) Terraform

- Add/update `azurerm_cognitive_deployment` for the new model.
- Update Key Vault secret (e.g. `azure-openai-endpoint-definitions`).

### B3) Node backend

- Add model to language-model enum and factory (API version, max tokens, endpoint mapping).
- **Token limits / API version:** Use values from model card or the ticket/PR; **link that source** in the PR description or code comment.

### B4) PR and apply

- Create PR; in the body **link to the Jira ticket and any PR/doc** that define deployment parameters (token window, API version, capacity).
- Review Terraform plan; if there is unexpected drift, stop and confirm with the user/infra.
- Apply via standard pipeline (e.g. Atlantis), one workspace at a time.

### B5) Verify

- Deployments visible in Azure portal.
- Roll **node-chat Deployment** (not HPA) to reload endpoint defs.
- Smoke test end-to-end.

---

## Track C — AI toolkit (if needed)

1. Check if the ai repo already has the model (merged or open PR).
2. If not: add enum + `LanguageModelInfo` + tests; in the PR or commit message **cite sources** (model card, LiteLLM registry, or ticket/PR for token limits and capabilities).
3. Release per normal toolkit process.

---

## Citing sources (required)

When you suggest or use any of the following, **always link to where the information came from**:

- **Token limits (input/output)** → Model card, vendor spec, or the Jira ticket/PR that specifies them.
- **Model ids / provider strings** → [LiteLLM model registry](https://models.litellm.ai/) or the deployment ticket/PR.
- **API version (Azure)** → Ticket, internal doc, or previous deployment PR.
- **Capacity / deployment names** → Jira ticket or rollout PR.

Example in a PR body or comment:

- “Token limits and API version per Jira UN-17948 and deployment doc: [link].”
- “Model id confirmed via https://models.litellm.ai/ (search: gpt-5.4).”

If you cannot find an authoritative source, **ask the user** and do not guess.

---

## Final checklist (every track)

- [ ] Correct env(s) and rollout order (e.g. qa → uat → prod).
- [ ] ArgoCD synced where applicable.
- [ ] **Deployment** rolled (not HPA).
- [ ] Smoke test with the exact model id users will request.
- [ ] Rollout notes and **source links** captured (Jira comment + PR/ticket links + timestamps).

---

## Rollback and safety

- **Do not** suggest Atlantis apply or production changes without explicit user approval.
- If Terraform drift or “model not discoverable” looks wrong: stop, explain, and suggest the smallest safe next step (e.g. verify secret, restart correct Deployment, split PRs).
- Do not change the process; follow this runbook and improve clarity around it.
