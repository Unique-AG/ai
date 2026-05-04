# uqadm

Admin CLI for the Unique platform: **list** spaces, **export** a space to JSON or YAML, **diff** two spaces, and **migrate** space (assistant) configuration between environments defined by per-slot env files. It is separate from `unique-cli` (the agent-oriented file explorer).

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
uqadm --cwd /path/to/secrets space list qa
uqadm --version
```

## `uqadm space`

Space-related commands. Run:

```bash
uqadm space --help
```

### `uqadm space list`

Lists spaces visible to the credentials in `.{SLOT}.env` or `{SLOT}.env` (see **Credential slots and env files**). Uses **`Space.get_spaces`** with pagination (`take` up to 1000 per page) until all pages are fetched.

**Syntax:**

```text
uqadm [GLOBAL_OPTS...] space list SLOT [OPTIONS]
```

| Argument / option | Required | Description |
|-------------------|----------|---------------|
| `SLOT` | Yes | Slot name; loads `.{SLOT}.env` or `{SLOT}.env` (under `--cwd` if set). |
| `--name TEXT` | No | Case-insensitive **partial** filter on space name; forwarded to the API. |
| `--json` | No | Print the full result list as JSON instead of a text table. |

**Table columns** (non-JSON): `id`, `name`, `uiType`, `isPinned`.

**Examples:**

```bash
uqadm space list 1
uqadm space list qa --name Report
uqadm space list prod --json
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
uqadm [GLOBAL_OPTS...] space export SPEC [-o PATH|--output PATH]
```

| Argument / option | Required | Description |
|-------------------|----------|-------------|
| `SPEC` | Yes | Same endpoint forms as **`migrate --source`**: `slot:space_id` or `slot:https://...` with a path containing `/space/<id>` (or `custom-space` / `swappable-intelligence-space`). A **space id is required**. |
| `-o`, `--output PATH` | No | Write the snapshot to this file; suffix must be **`.json`**, **`.yaml`**, or **`.yml`**. Parent directories are created if needed. Default: **stdout** (JSON only). |

**Examples:**

```bash
uqadm space export "1:space_abc123"
uqadm space export "qa:https://example.com/app/space/space_xyz" -o backup.json
uqadm space export "qa:space_xyz" -o backup.yaml
```

---

### `uqadm space diff`

Loads two spaces (two **`Space.get_space`** calls, potentially via **different** slots/env files), renders each side as **canonical JSON**, and prints a **unified diff** (`difflib.unified_diff`).

**Syntax:**

```text
uqadm [GLOBAL_OPTS...] space diff --a SPEC --b SPEC [OPTIONS]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--a SPEC` | Yes | First space (`slot:space_id` or `slot:URL` with extractable id); same rules as **`migrate --source`**. |
| `--b SPEC` | Yes | Second space (same spec forms). |
| `--ignore-timestamps` | No | Before comparing, **remove** every `createdAt` and `updatedAt` key **recursively** from both payloads (useful to hide churn from timestamps only). |

**Exit codes:**

| Code | Meaning |
|------|---------|
| `0` | No differences after normalization (or only suppressed timestamps when `--ignore-timestamps` makes payloads identical). |
| `1` | Differences found (**stdout** contains the diff) **or** an unexpected API/network error during fetch. |
| `2` | Invalid endpoint spec (e.g. missing space id). |

**Examples:**

```bash
uqadm space diff --a "1:space_a" --b "1:space_b"
uqadm space diff --a "qa:space_x" --b "prod:space_y" --ignore-timestamps
```

---

### `uqadm space migrate`

Copies assistant configuration from a **source** space to a **destination** (either a **new** space on the destination slot or an **existing** space id).

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

#### Endpoint spec (`migrate --source` / `--destination`, and **`export` / `diff`** where a space id is required)

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

## Python module entry

```bash
python -m uqadm --help
```

## Related

- **`unique-cli`** — SDK file-explorer CLI (`unique_sdk`); unchanged by `uqadm`.
- **`unique_sdk.cli.config`** — `load_config()` and env semantics shared with `unique-cli`.
