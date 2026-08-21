# Unique SDK integration tests

Live API tests under `unique_sdk/tests/integration/`. They call a real gateway
(typically QA), write inspectable artifacts, and are **excluded** from the
default `pytest` / `poe test` suite.

## Setup

From `unique_sdk/`:

```bash
cp tests/integration/.testenv.example tests/integration/.testenv
```

Fill in `.testenv` (gitignored):

| Variable | Required | Purpose |
|---|---|---|
| `UNIQUE_API_KEY` | yes | Bearer auth |
| `UNIQUE_APP_ID` | yes | App header |
| `UNIQUE_USER_ID` | yes | Request user |
| `UNIQUE_COMPANY_ID` | yes | Request company |
| `UNIQUE_API_BASE` | yes | Public chat gateway (default in example: QA `…/public/chat-gen2`) |
| `UNIQUE_ASSISTANT_ID` | no | Reuse an existing space; otherwise a temporary UniqueAI space is created |
| `UNIQUE_SCOPE_ID` | no | Used as `skillChoices.scopeId` when set |

Variable names match **unique-cli**.

## Run

Always pass `-m integration` (or use the Poe task). A path alone is not enough
because `pyproject.toml` defaults to `-m 'not integration'`.

```bash
cd unique_sdk

# This package only (preferred)
uv run poe test-integration

# Same, with live stdout (artifact paths)
uv run pytest tests/integration -m integration -s

# Language-model override tests only
uv run pytest tests/integration/test_space_create_message_language_model.py -m integration -s

# Older api_resources live tests (different env: tests/integration_test.env)
uv run pytest tests/api_resources -m integration -s
```

`-s` prints the artifact directory path for each test.

## What is covered

| File | Focus |
|---|---|
| `test_space_create_message.py` | `Space.create_message` accepts extended request fields (`skillChoices`, `availableSkills`, `selectedUploadedFileIds`, …) |
| `test_space_create_message_language_model.py` | Per-message `languageModel` override; asks the model which model it is; asserts `llm_invocations` |

Model group names for the language-model tests are hardcoded in
`LANGUAGE_MODELS_UNDER_TEST` (not secrets). Edit that tuple to change which
models QA exercises.

## Artifacts

Each run writes under:

```text
tests/integration/artifacts/<test_name>/<utc_timestamp>/
```

Typical files:

- `meta.json` — test id, API base, retention settings (no secrets)
- `create_message_request.json` / `create_message_response.json`
- `assistant_answer.txt` — plain-text reply (language-model tests)
- `assistant_message.json`, `llm_invocations.json`, `manual_inspection.json`

`artifacts/` is gitignored. Retention (applied when a new run is created for
that test):

- delete run dirs older than **2 days**
- keep at most **20** newest runs per test

## Notes

- Use the default SDK API version (`2023-12-06`). node-chat public space routes
  are registered for that version only; sending `x-api-version: 2026-03-01`
  yields `404 Cannot POST /public/space/message`.
- `languageModel` on create-message may require manage access and a space with
  model switching configured for the requested model.
- Temporary spaces created when `UNIQUE_ASSISTANT_ID` is unset are deleted after
  the module finishes; prefer a stable assistant id if you want to open chats
  in the UI after the run.
