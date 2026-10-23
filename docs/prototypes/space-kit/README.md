# space-kit (reference prototype)

> **Reference code, not a package.** This is a working prototype shared so
> nobody has to rediscover how to create Conduct spaces through the public
> API (UN-27050). It is not wired into `uqadm`, not released, and not
> reviewed as production code. Take what is useful. The optional
> "harness-eval registration" feature is specific to an internal eval
> setup and can be ignored or deleted (`register.py` and its tests).
> `pyproject.reference.toml` is the project file; copy it to
> `pyproject.toml` to run the tests (named differently so CI does not treat
> this folder as a package).

Create, edit and delete Conduct spaces on **local** and **QA** with one
command, with the same result as clicking through the UI: harness, model,
effort, every module config key, settings, MCP servers and tools, prompts,
access.

It talks to the node-chat public API (`2023-12-06`), which accepts
`uiType: SWAPPABLE_INTELLIGENCE` and `mcpServers` on `POST /space` and
`PATCH /space/{id}`. Dependencies: `pydantic` and `pyyaml`. HTTP is stdlib
`urllib`.

## Why clone, not create from scratch

The public API stores whatever module config you send. It does not fill in
the defaults the UI applies, and it cannot set scope rules, the allow-list
of space-restricted MCP servers, or the copy button. So space-kit always
starts from a **template space** (one you configured in the UI), copies it
in full, and applies your overlays. Anything it cannot copy is printed as a
warning.

## Setup

```bash
cd docs/prototypes/space-kit
cp pyproject.reference.toml pyproject.toml
cp envs.example.yaml envs.yaml   # paths to env files, never values
python3 -m space_kit envs        # shows which env file each target uses
```

Env files may use harness-eval names (`UNIQUE_APP_KEY`, `UNIQUE_API_BASE`,
`UNIQUE_APP_ID`, `UNIQUE_USER_ID`, `UNIQUE_COMPANY_ID`) or uqadm names
(`UNIQUE_API_KEY`, `UNIQUE_BASE_URL`, ...). Order: `--env-file`, then
`SPACE_KIT_ENV_FILE_QA` / `SPACE_KIT_ENV_FILE_LOCAL`, then `envs.yaml`.
A file whose API base points at another target is refused, and so is any
host other than localhost or a `qa` host under `QA_DOMAIN` (set it in
`space_kit/env.py` for your deployment; prod and other stages are refused).

## Commands

Every write is a dry run unless you pass `--yes`. A dry run prints the
change list and writes the exact payload to `ledger/dry-runs/`.

```bash
# Look
python3 -m space_kit mcp --env qa                      # servers, ids, callable tools
python3 -m space_kit show <space_id> --env qa          # every config path and value
python3 -m space_kit show <space_id> --env qa --prefix claude   # one section
python3 -m space_kit diff <a> <b> --env qa             # what differs
python3 -m space_kit diff <a> <b> --env qa --env-right local    # across targets

# Create
python3 -m space_kit clone <template_id> --env qa --name variant-effort-low \
  --set claude.effort=low                              # dry run
python3 -m space_kit clone ... --yes                   # create, then re-read and verify
python3 -m space_kit apply specs/examples/effort-low.yaml [--yes]

# Change
python3 -m space_kit edit <space_id> --env qa --set codex.model=... --yes
python3 -m space_kit grant <space_id> --env qa --grant GROUP:<id>:USE --yes

# Clean up (only spaces this machine created, see ledger)
python3 -m space_kit delete <space_id> --env qa --yes
python3 -m space_kit ledger
```

### Changing things

| Flag | Changes | Example |
|---|---|---|
| `--set PATH=VALUE` | module config | `claude.effort=low`, `setup.agentMdInstructions=@file:agent.md` |
| `--setting PATH=VALUE` | space settings | `allowUserMemory=false` |
| `--space-field F=V` | space fields | `alert=...`, `languageModel=...`, `assistantPrompts=@file:p.json` |
| `--explanation TEXT` | space description | |
| `--mcp SERVER=all\|none\|t1,t2` | MCP selection | `GitHub MCP=all`, `mcp_abc=none` |
| `--mcp-replace` | start with no MCP servers | |
| `--grant TYPE:ID:ACCESS` | access after create | `USER:<id>:MANAGE` |

Values are JSON when they parse (`true`, `5`, `["a"]`), `@file:<path>` reads
a file, anything else is a string. Paths are dotted; list entries are picked
by name: `tools[WebSearch].isEnabled=false`, or `tools[search@mcp_abc]` when
two servers have a tool with the same name. A path that does not exist is
refused with the known keys listed (typo guard); `--allow-new-keys` lets it
through. Run `show` on the template first to see the exact keys.

Keys per harness: claude `claude.model`, `claude.effort`; codex
`codex.model`, `codex.modelReasoningEffort`; Pi `piAgent.modelName`,
`piAgent.thinkingLevel`; harness choice `strategy`.

### MCP

The selection lives in two places: the attachment tables (what the runtime
reads) and the MCP entries in `configuration.tools`. space-kit keeps both
in line. Rules it applies:

- A server name that is not unique (QA has several `mcp.atlassian.com`)
  must be given by id. `mcp` lists the ids.
- Tools the server no longer exposes are left out of the attachment (the
  API rejects them) with a warning; their module config entries stay as
  they were, so harness-eval fingerprints match the template.
- Space-restricted servers cannot be attached through the API. The
  command fails and says what to do in the UI; `--skip-restricted` drops
  them with a warning instead.

### Cross-environment clones

`clone <id> --from-env qa --env local` reads the template on QA and creates
on local. MCP ids are matched by unique server name; give the rest with
`--mcp-map SRC=DST` or drop them with `--drop-unmapped-mcp`. Scope rules
and folder ids are environment specific and are reported.

### harness-eval registration (opt-in)

`--register PROFILE` appends the new space to
`../harness-eval/spaces.yaml` after creating it. Model and thinking are read
from the config, `derived_from` is the profile of the template, and
`changed_key` is inferred when exactly one path changed (otherwise pass
`--changed-key`). The entry is validated with harness-eval's own loader on
a copy before the real file is replaced, and problems are found before the
space is created. `--doctor` runs `doctor --live` for the new profile.
Without `--register`, harness-eval is never touched.

## Exit codes

`0` done, `1` error (nothing written unless the message says so), `2`
created but the re-read did not match (read the diff it prints).

## Tests

```bash
python3 -m pytest -q          # offline; fake API, no network
ruff check space_kit tests && ruff format --check space_kit tests
basedpyright                  # package only, like harness-eval
```

## What is reusable for uqadm (UN-27050)

Verified against a QA deployment: a Conduct space (`SWAPPABLE_INTELLIGENCE`
with harness, model and effort in the module config, plus MCP selection) can
be created, read back and deleted through the public API. **Not verified:**
`uqadm` export then upsert of a Conduct space; this prototype does not use
`uqadm`.

Pieces worth lifting:

- `payload.py`: clone a template space into a create payload and apply
  overlays. Never create from a sparse config; the API does not apply the
  UI defaults.
- `workflow.verify_created`: read the new space back and diff it against
  what was sent (exit code 2 when they differ).
- `mcp.py`: edge cases when a selection is sent. Server names are not
  unique, tools a server no longer exposes are rejected by the API,
  space-restricted servers cannot be attached on create, MCP tools also
  live in `configuration.tools` and must be kept in line with the
  attachments, and server ids differ between environments.
- `paths.py`: typo-safe dotted config paths for overrides.

The public API cannot set scope rules, the allow-list of space-restricted
MCP servers, or the copy button.
