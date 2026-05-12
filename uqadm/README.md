# uqadm

Admin CLI for the Unique platform: **list** spaces, **export** a space to JSON or YAML, **upsert** from such a snapshot (create or update on a slot), **diff** two spaces, **migrate** assistant configuration between slots/environments, and **delete** a space — all via per-slot env files. It is separate from `unique-cli` (the agent-oriented file explorer).

Configuration is normalized into the same **`UNIQUE_*`** variables that **`unique_sdk.cli.config.load_config()`** expects (same path as `unique-cli`). You may mix **SDK** names with **toolkit** names from `unique_toolkit` settings: **`unique_auth_*`** (user/company), **`unique_app_key`** / **`unique_app_id`** (API key / app id, same as `UniqueApp`), and **`unique_api_base_url`** (gateway base, same as `UniqueApi`). Uppercase variants like **`UNIQUE_APP_KEY`** and **`UNIQUE_API_BASE_URL`** are also accepted. If both a `UNIQUE_*` variable and its toolkit alias are set, **`UNIQUE_*` wins**. Bare names like `KEY` or `BASE_URL` are **not** read (too ambiguous).

## Installation

From the AI monorepo root (workspace package):

```bash
cd /path/to/ai
uv sync --package uqadm
uv run uqadm --help
```

Or install the `uqadm` package in any environment that already has `unique-sdk` and run `uqadm` on your `PATH`.

## Credential slots and env files

Commands refer to an environment by **slot** — a short label you choose (e.g. `1`, `qa`, `prod`).

For slot `<slot>`, credentials are read from **one** of these files under the chosen directory (see resolution order below):

```text
.{slot}.env
{slot}.env
```

Resolved relative to the **current working directory**, unless you pass **`uqadm --cwd <DIR>`** (see below).

**Which file is used:** if **`.{slot}.env`** exists, it is loaded; otherwise if **`{slot}.env`** exists, that is loaded. If **both** exist, the **hidden** file (`.{slot}.env`) wins. If neither exists, `uqadm` prints a short guide to **stderr** (which directory was searched, the exact filenames, required variables, and how to use `--cwd`) and exits with code **2** — no Python traceback.

Before loading a slot file, `uqadm` **clears** SDK `UNIQUE_*` variables, optional `UNIQUE_API_*` / `UNIQUE_APP_ID`, and toolkit keys (`unique_auth_*`, `unique_app_*`, `unique_api_*`, plus selected `UNIQUE_*` toolkit aliases) so values from a previous slot do not leak.

| Variable | Purpose |
|----------|---------|
| `UNIQUE_USER_ID` | **Required** for API calls (unless you set one of the aliases below). |
| `unique_auth_user_id` or `UNIQUE_AUTH_USER_ID` | Alternative to `UNIQUE_USER_ID` (same meaning as in `unique_toolkit` `UniqueAuth`). Ignored if `UNIQUE_USER_ID` is set. |
| `UNIQUE_COMPANY_ID` | **Required** for API calls (unless you set one of the aliases below). |
| `unique_auth_company_id` or `UNIQUE_AUTH_COMPANY_ID` | Alternative to `UNIQUE_COMPANY_ID`. Ignored if `UNIQUE_COMPANY_ID` is set. |
| `UNIQUE_API_KEY` | Optional (not needed on localhost / secured cluster per SDK docs). |
| `unique_app_key` or `UNIQUE_APP_KEY` | Alternative to `UNIQUE_API_KEY` (`UniqueApp.key`). Ignored if `UNIQUE_API_KEY` is set. |
| `UNIQUE_APP_ID` | Optional (same as SDK docs). |
| `unique_app_id` | Alternative to `UNIQUE_APP_ID` (`UniqueApp.id`). Ignored if `UNIQUE_APP_ID` is set. |
| `UNIQUE_API_BASE` | Optional; default applied inside `load_config()` if unset. |
| `unique_api_base_url` or `UNIQUE_API_BASE_URL` | Alternative to `UNIQUE_API_BASE` (`UniqueApi.base_url`). Ignored if `UNIQUE_API_BASE` is set. **Host-only** URLs (no path, or `/` only) get **`/public/chat`** appended (e.g. `https://gateway.example` → `https://gateway.example/public/chat`). If the URL **already includes a path** (e.g. `http://localhost:8092/public` or `…/public/chat-gen2`), it is copied to **`UNIQUE_API_BASE` unchanged**. |

The file is loaded with **`python-dotenv`** (`override=True`) so keys in the file replace any existing values for that load.

If an API call fails with something that looks like **authentication** (HTTP **401**, `AuthenticationError`, or messages containing **“unauthorized”** / **“401”**), `uqadm` prints an extra **credential snapshot** to **stderr**: resolved `UNIQUE_USER_ID`, `UNIQUE_COMPANY_ID`, `UNIQUE_APP_ID`, `UNIQUE_API_BASE`, and a **redacted** description of `UNIQUE_API_KEY` (never the full key), plus HTTP status / `Request-Id` when the SDK exposes them. This matches what was passed into the SDK after env normalization.

Example **`.1.env`** (or non-hidden **`1.env`** with the same contents):

```bash
UNIQUE_USER_ID=user_...
UNIQUE_COMPANY_ID=company_...
UNIQUE_API_KEY=ukey_...
UNIQUE_APP_ID=app_...
UNIQUE_API_BASE=https://gateway.unique.app/public/chat-gen2
```

Or the same credentials using toolkit-style names (no `UNIQUE_*` lines required except where you prefer them):

```bash
unique_auth_user_id=user_...
unique_auth_company_id=company_...
unique_app_key=ukey_...
unique_app_id=app_...
unique_api_base_url=https://gateway.unique.app/public/chat-gen2
```

## Global options

These apply to all subcommands (they must appear **before** the subcommand group).

| Option | Description |
|--------|-------------|
| `--help` | Show help and exit. |
| `--version` | Print `uqadm` version and exit. |
| `--cwd DIRECTORY` | Directory in which per-slot env files (`.{slot}.env` or `{slot}.env`) are resolved. Default: process current working directory. Must be an existing directory. |

**Examples:**

```bash
uqadm --cwd /path/to/secrets space list --slot qa
uqadm --version
```

## CLI operand flags

Every subcommand uses **named options** for required operands (no bare `SPEC` / `SLOT` positionals):

| Flag | Used for |
|------|----------|
| **`--slot SLOT`** | **`space list`** — which credential env file to load (not a space id). |
| **`--source SPEC`** | **`space export`**, **`space delete`**, **`space migrate --source`**, and **`space diff`** (first space). |
| **`--destination SPEC`** | **`space migrate --destination`**, **`space upsert`**, and **`space diff`** (second space). |
| **`--file` / `-f`** | **`space upsert`** — local snapshot path. |

## `uqadm space`

Space-related commands. Run:

```bash
uqadm space --help
```

### `uqadm space list`

Lists spaces visible to the credentials in `.{SLOT}.env` or `{SLOT}.env` (see **Credential slots and env files**). Uses **`Space.get_spaces`** with pagination (`take` up to 1000 per page) until all pages are fetched.

**Syntax:**

```text
uqadm [GLOBAL_OPTS...] space list --slot SLOT [OPTIONS]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--slot SLOT` | Yes | Slot name; loads `.{SLOT}.env` or `{SLOT}.env` (under `--cwd` if set). |
| `--name TEXT` | No | Case-insensitive **partial** filter on space name; forwarded to the API. |
| `--json` | No | Print the full result list as JSON instead of a text table. |

**Table columns** (non-JSON): `id`, `name`, `uiType`, `isPinned`.

**Examples:**

```bash
uqadm space list --slot 1
uqadm space list --slot qa --name Report
uqadm space list --slot prod --json
```

---

### `uqadm space export`

Fetches a single space via **`Space.get_space`**. The payload is normalized the same way for every output path: **`json.dumps(..., sort_keys=True, default=str)`** then **`json.loads`**, so values match canonical JSON semantics before writing.

- **No `-o`**: prints **canonical JSON** to stdout (`indent=2`, sorted keys).
- **With `-o PATH`**: the file **suffix** selects the format (case-insensitive):
  - **`.json`** — canonical JSON (`indent=2`, sorted keys).
  - **`.yaml`** or **`.yml`** — YAML for easier editing of long prompts. Multi-line strings are written as **literal block scalars** (`|`), similar to the internal **config-converter** tool, so **Jinja**-style `{{` / `{%` in text stays readable. The same heuristic as config-converter turns literal two-character `\` + `n` sequences into newlines and trims spaces before newlines when choosing block style; if you must preserve a literal `\n` in a string, be aware of that edge case.

If `-o` is set but the suffix is **missing** or **not** one of `.json`, `.yaml`, or `.yml`, the command **exits with code 2** and prints an error listing the allowed suffixes.

**Syntax:**

```text
uqadm [GLOBAL_OPTS...] space export --source SPEC [-o PATH|--output PATH]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--source SPEC` | Yes | Same endpoint forms as **`migrate --source`**: `slot:space_id` or `slot:https://...` with a path containing `/space/<id>` (or `custom-space` / `swappable-intelligence-space`). A **space id is required**. |
| `-o`, `--output PATH` | No | Write the snapshot to this file; suffix must be **`.json`**, **`.yaml`**, or **`.yml`**. Parent directories are created if needed. Default: **stdout** (JSON only). |

**Examples:**

```bash
uqadm space export --source "1:space_abc123"
uqadm space export --source "qa:https://example.com/app/space/space_xyz" -o backup.json
uqadm space export --source "qa:space_xyz" -o backup.yaml
```

To push an edited snapshot back onto the API (inverse of export), use **`uqadm space upsert`** below.

---

### `uqadm space upsert`

Reads a **local snapshot** file (JSON or YAML with the same suffix rules as **`space export`**) and either **creates** a new space or **updates** an existing one on the destination slot. Behavior matches **`space migrate`** create/update paths (same `Space.create_space` / `Space.update_space` field mapping, module matching **by name**, and **`add_space_access`** from snapshot `assistantAccess`).

- **Create**: **`--destination`** is **`slot`** or **`slot:`** only (no space id). The snapshot must include **`name`** and **`fallbackModule`** (same as migrate create).
- **Update**: **`--destination`** is **`slot:space_id`** or **`slot:https://...`** (space id required). The snapshot must include a non-null **`name`**; modules are merged into the destination by name like migrate.

Warnings for **scope rules** and **MCP server bindings** in the snapshot mirror migrate (they are not applied via this command).

If the file suffix is not **`.json`**, **`.yaml`**, or **`.yml`**, or the root document is not a JSON object, the command **exits with code 2**.

**Syntax:**

```text
uqadm [GLOBAL_OPTS...] space upsert --destination SPEC -f FILE|--file FILE [OPTIONS]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--destination SPEC` | Yes | Space endpoint to create or update: same forms as **`migrate --destination`** (`slot` / `slot:` to create; `slot:space_id` or `slot:URL` to update). |
| `-f`, `--file FILE` | Yes | Path to snapshot (`.json`, `.yaml`, or `.yml`). |
| `--dry-run` | No | Do **not** call create/update or `add_space_access`; may still call **`get_space`** when updating to preview module mapping. |

**Examples:**

```bash
uqadm space upsert --destination "2:" --file backup.yaml
uqadm space upsert --destination "qa:space_dst456" -f ./edited.json --dry-run
```

---

### `uqadm space diff`

Loads two spaces (two **`Space.get_space`** calls, potentially via **different** slots/env files), canonicalizes JSON (`sort_keys`, stable stringification), then compares.

**Default (recommended):** both payloads are **normalized** before compare: recursively drops common ephemeral keys so you see **meaningful config drift**, not noise from ids and timestamps:

`createdAt`, `updatedAt`, `id`, `moduleId`, `companyId`, `createdBy`, `updatedBy`

Use **`--strict`** to compare **raw** API payloads (no stripping).

**Display**

| `--format` | Behaviour |
|------------|-----------|
| **`unified`** (default) | If **stdout is a TTY**: Rich **two-column** view with **inline word-level** red/green highlights (similar to many editors’ split diff). If **not a TTY** (pipe/file): classic **`difflib.unified_diff`** text. |
| **`side-by-side`** | Two **syntax-highlighted JSON** panes (Rich), best on a **wide** terminal — good for scanning whole structures after normalization. |

**Syntax:**

```text
uqadm [GLOBAL_OPTS...] space diff --source SPEC --destination SPEC [OPTIONS]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--source SPEC` | Yes | First space (`slot:space_id` or `slot:URL` with extractable id); same rules as **`migrate --source`**. |
| `--destination SPEC` | Yes | Second space (same spec forms). |
| `--strict` | No | Compare **full** payloads (keep ids, timestamps, etc.). |
| `--format` | No | `unified` (default) or `side-by-side`; see **Display** table. |

**Exit codes:**

| Code | Meaning |
|------|---------|
| `0` | No differences after the chosen normalization / strict compare. |
| `1` | Differences remain **or** an unexpected API/network error during fetch. |
| `2` | Invalid endpoint spec (e.g. missing space id). |

**Examples:**

```bash
uqadm space diff --source "1:space_a" --destination "1:space_b"
uqadm space diff --source "qa:space_x" --destination "prod:space_y" --format side-by-side
uqadm space diff --source "qa:x" --destination "prod:y" --strict
```

---

### `uqadm space migrate`

Copies assistant configuration from a **source** space to a **destination** (either a **new** space on the destination slot or an **existing** space id). To apply a **local snapshot file** instead of copying from another live space, use **`uqadm space upsert`**.

**Syntax:**

```text
uqadm [GLOBAL_OPTS...] space migrate --source SPEC --destination SPEC [OPTIONS]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--source SPEC` | Yes | Source endpoint (see **Endpoint spec** below). A space id is **required** (plain id or extracted from a URL). |
| `--destination SPEC` | Yes | Destination endpoint (see **Endpoint spec** below). Space id **optional** — omit or use `slot:` / `slot` only to **create** a new space. |
| `--dry-run` | No | Do **not** call create/update or `add_space_access`. Still performs **read** calls (`get_space`, etc.) to build the preview where applicable. |
| `--with-knowledge` | No | Reserved for same-environment extended migration; currently **informational only** (messages when scope rules exist; does not migrate folders/content graphs via API). |

#### Endpoint spec (`--source` / `--destination` space endpoints)

Used by **`space export --source`**, **`space delete --source`**, **`space diff --source` / `--destination`**, **`space migrate`**, and **`space upsert --destination`** (and **`migrate --source` / `--destination`**).

The spec string selects:

1. Which **slot env file** to load (`slot`): `.{slot}.env` or `{slot}.env` (same resolution as elsewhere).
2. Optionally which **space id** to use (`space_id`).

**Parsing rules:**

- Split on the **first** colon only: `slot` = left side (trimmed), remainder = right side (trimmed).
- If there is **no** colon, the whole string is the **`slot`** and **`space_id` is omitted** (valid only for **destination** when creating a new space).
- If there is a colon and the right side is **empty** after trimming (`2:`), **`space_id` is omitted** (create on destination slot `2`).
- If the right side starts with **`http://`** or **`https://`**, it is treated as a URL: **`space_id`** is parsed from the URL path (see **URL paths** below).

**Examples:**

| Spec | Slot | Space id | Meaning |
|------|------|----------|---------|
| `1` | `1` | *(none)* | Destination: create new space using slot `1` env (`.1.env` or `1.env`). |
| `2:` | `2` | *(none)* | Same as above. |
| `1:space_abc123` | `1` | `space_abc123` | Space `space_abc123` using slot `1` credentials. |
| `prod:https://host/app/space/space_xyz` | `prod` | `space_xyz` | Credentials from slot `prod` env; id parsed from URL path. |

**Supported URL path shapes** (segment after the marker must not be `create`):

- `.../space/<id>`
- `.../custom-space/<id>`
- `.../swappable-intelligence-space/<id>`

**Typical flows:**

- **Create** new space on destination slot `2` from source slot `1`:

  ```bash
  uqadm space migrate --source "1:space_src123" --destination "2:"
  ```

- **Update** existing destination space:

  ```bash
  uqadm space migrate --source "1:space_src123" --destination "2:space_dst456"
  ```

#### Migrate behavior (summary)

- **Cross-environment** (different `UNIQUE_COMPANY_ID` or normalized `UNIQUE_API_BASE` between source and destination): warns that folder/knowledge-linked scope data is not copied; scope rules are skipped; MCP server bindings are not migrated (warning).
- **Create**: builds `Space.create_space` from source snapshot (modules without instance ids, settings, etc.).
- **Update**: matches modules **by name** between source and destination; sends `update_space` with destination **`moduleId`** values; warns on unmatched source modules.
- After create/update, attempts **`add_space_access`** from source `assistantAccess`; failures are warned, not fatal.
- **`--dry-run`**: skips create/update/access writes; may still call read APIs to describe actions.

For edge cases and API limits, see the implementation in `uqadm/space_migrate.py`.

---

### `uqadm space delete`

Deletes one space via **`Space.delete_space`**. Fetches the space first (**`Space.get_space`**) to show **id**, **name**, and **uiType** in the confirmation prompt (unless you skip the prompt).

**Syntax:**

```text
uqadm [GLOBAL_OPTS...] space delete --source SPEC [OPTIONS]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--source SPEC` | Yes | Same endpoint forms as **`migrate --source`** / **`space export --source`**: `slot:space_id` or `slot:https://...` with extractable id. A **space id is required**. |
| `-y`, `--yes` | No | Skip the interactive confirmation prompt. |
| `--dry-run` | No | Still calls **`get_space`** to resolve the space; prints what would be deleted without calling **`delete_space`**. |

If you decline the confirmation prompt, the command exits **0** and prints `Aborted.`

**Examples:**

```bash
uqadm space delete --source "1:space_old123"
uqadm space delete --source "prod:https://host/app/space/space_x" --dry-run
uqadm space delete --source "qa:space_x" -y
```

## Python module entry

```bash
python -m uqadm --help
```

## Related

- **`unique-cli`** — SDK file-explorer CLI (`unique_sdk`); unchanged by `uqadm`.
- **`unique_sdk.cli.config`** — `load_config()` and env semantics shared with `unique-cli`.
