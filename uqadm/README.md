# uqadm

Admin CLI for the Unique platform. It groups these command families:

- **`space`** — list, export, diff, migrate, upsert, access grants, ingestion settings, and delete assistant spaces.
- **`kb`** — knowledge-base folders: create paths, grant group access, set folder ingestion config.
- **`chat`** — send messages to an assistant and inspect chat history.
- **`env`** — manage named credential slots stored in `~/.uqadm/envs/`.
- **`install`** — one-time bootstrap: create directories, install shell completion, set up your first slot.

It is separate from `unique-cli` (the agent-oriented file explorer) and shares the same `UNIQUE_*` environment variable conventions as `unique_sdk`.

---

## Installation

From the AI monorepo root:

```bash
cd /path/to/ai
uv sync --package uqadm
uv run uqadm --help
```

Or install the `uqadm` package into any environment that already has `unique-sdk`:

```bash
pip install -e uqadm/
uqadm --help
```

---

## `uqadm install`

One-time bootstrap for a new machine or user. Safe to re-run (idempotent).

```bash
uqadm install                           # interactive
uqadm install --dry-run                 # preview without changes
uqadm install --no-rc                   # skip rc file patching
uqadm install --shell bash              # force bash (auto-detected by default)
uqadm install --rc-file ~/.zshrc        # explicit rc file path
```

What it does:

1. Creates `~/.uqadm/` (mode `0700`) and `~/.uqadm/envs/`.
2. Installs shell completion for `uqadm`.
3. Offers to create your first credential slot interactively (skipped if slots already exist).
4. Appends an idempotent `export UQADM_HOME=...` block to your shell rc file.

| Option | Description |
|--------|-------------|
| `--dry-run` | Print what would be done without making any changes. |
| `--no-rc` | Skip patching the shell rc file. |
| `--shell SHELL` | Shell to configure: `zsh` or `bash` (auto-detected from `$SHELL`). |
| `--rc-file PATH` | Explicit path to the rc file to patch. |

---

## Quick start

```bash
# 1. Bootstrap directories, shell completion, and first credential slot
uqadm install

# 2. (Optional) add more slots or set a different default
uqadm env create prod --set-default

# 3. List spaces — uses the configured default slot
uqadm space list

# 4. Send a message to an assistant
uqadm chat send asst_abc123 --text "Hello!"

# 5. Continue the same thread using the chat_id printed after step 4
uqadm chat send asst_abc123 --text "Tell me more" --chat-id chat_xyz789
```

---

## Credential slots

A **slot** is a short name (e.g. `qa`, `prod`, `1`) that maps to a `.env` file holding `UNIQUE_*` credentials.

### File locations (resolution order)

1. `~/.uqadm/envs/.{slot}.env` — managed by `uqadm env create`; this is the primary location.
2. If not found there, falls back to the **current working directory** (or `--cwd` if set):
   - `.{slot}.env` (hidden file wins)
   - `{slot}.env`

If no file is found, `uqadm` prints a short guide to stderr and exits with code **2** — no Python traceback.

### Default slot

Running `uqadm env set-default qa` writes the default slot to `~/.uqadm/config.toml`. All commands that accept `--slot` will use this default when the option is omitted.

### Env file format

```bash
# ~/.uqadm/envs/.qa.env
UNIQUE_USER_ID=user_...
UNIQUE_COMPANY_ID=company_...
UNIQUE_API_KEY=ukey_...
UNIQUE_APP_ID=app_...
UNIQUE_API_BASE=https://unique_api_base_url
```

Toolkit-style names are also accepted (lowercase `unique_auth_user_id`, `unique_app_key`, etc.). If both `UNIQUE_*` and its alias are present, `UNIQUE_*` wins.

### Supported variables

| Variable | Required | Notes |
|----------|----------|-------|
| `UNIQUE_USER_ID` | Yes | Also: `unique_auth_user_id` / `UNIQUE_AUTH_USER_ID` |
| `UNIQUE_COMPANY_ID` | Yes | Also: `unique_auth_company_id` / `UNIQUE_AUTH_COMPANY_ID` |
| `UNIQUE_API_KEY` | No | Also: `unique_app_key` / `UNIQUE_APP_KEY` |
| `UNIQUE_APP_ID` | No | Also: `unique_app_id` |
| `UNIQUE_API_BASE` | No | Also: `unique_api_base_url` / `UNIQUE_API_BASE_URL`. Host-only URLs get `/public/chat` appended automatically. |

### Authentication debug output

If an API call fails with HTTP 401 or an authentication error, `uqadm` prints a redacted credential snapshot to stderr (user id, company id, app id, base URL, and a masked description of the API key — never the full key).

---

## Global options

These must appear **before** the subcommand:

| Option | Description |
|--------|-------------|
| `--help` / `-h` | Show help and exit. |
| `--version` | Print `uqadm` version and exit. |
| `--cwd DIRECTORY` | Override the directory used for local env file lookup. |

```bash
uqadm --version
uqadm --cwd /path/to/secrets space list --slot qa
```

---

## `uqadm env`

Manage credential slots in `~/.uqadm/envs/`.

```bash
uqadm env --help
```

### `env create SLOT`

Interactively (or non-interactively) create a credential slot file at `~/.uqadm/envs/.{SLOT}.env`.

```bash
uqadm env create qa
uqadm env create prod --set-default
uqadm env create staging --force               # overwrite if already exists
uqadm env create ci --non-interactive \
  --user-id user_abc \
  --company-id company_xyz \
  --api-key ukey_... \
  --api-base https://gateway.unique.app/public/chat-gen2
```

| Option | Description |
|--------|-------------|
| `--set-default` | Mark this slot as the default after creation. |
| `--force` | Overwrite an existing slot file without prompting. |
| `--non-interactive` | Skip prompts; supply values via flags below. |
| `--user-id TEXT` | `UNIQUE_USER_ID` value. |
| `--company-id TEXT` | `UNIQUE_COMPANY_ID` value. |
| `--api-key TEXT` | `UNIQUE_API_KEY` value (optional). |
| `--app-id TEXT` | `UNIQUE_APP_ID` value (optional). |
| `--api-base TEXT` | `UNIQUE_API_BASE` value (optional). |

### `env list`

List all available slots; the default slot is marked with `*`.

```bash
uqadm env list
# * qa
#   prod
#   staging
```

### `env show [SLOT]`

Print the resolved credential values for a slot (API key is redacted). Omit `SLOT` to use the default.

```bash
uqadm env show
uqadm env show prod
```

### `env set-default SLOT`

Set the default slot written to `~/.uqadm/config.toml`.

```bash
uqadm env set-default prod
```

### `env delete SLOT`

Remove the env file for a slot (prompts for confirmation unless `-y`).

```bash
uqadm env delete staging
uqadm env delete staging -y
```

---

## `uqadm space`

Space administration commands.

```bash
uqadm space --help
```

### `space list`

List all spaces visible to the resolved slot credentials.

```bash
uqadm space list                        # uses default slot
uqadm space list --slot qa
uqadm space list --slot prod --name Report
uqadm space list --slot prod --json
```

| Option | Description |
|--------|-------------|
| `--slot SLOT` | Credential slot (default: configured default slot). |
| `--name TEXT` | Case-insensitive partial filter on space name. |
| `--json` | Print full result as JSON instead of a table. |

### `space export SPACE_ID`

Export a space snapshot to stdout (JSON) or a file.

```bash
uqadm space export space_abc123                              # JSON to stdout
uqadm space export space_abc123 --slot prod
uqadm space export space_abc123 -o backup.yaml              # YAML file
uqadm space export space_abc123 -o backup.json
```

| Option | Description |
|--------|-------------|
| `SPACE_ID` | Space id or `https://` URL containing `/space/<id>`. |
| `--slot SLOT` | Credential slot (default: configured default slot). |
| `-o`, `--output PATH` | Write to file; suffix must be `.json`, `.yaml`, or `.yml`. Default: stdout. |

### `space upsert`

Create or update a space from a local snapshot file. Omit `--target` to create a new space; provide `--target` to update an existing one.

```bash
uqadm space upsert -f backup.yaml                            # create on default slot
uqadm space upsert -f backup.yaml --slot qa                  # create on specific slot
uqadm space upsert -f edited.json --target space_dst456      # update existing space
uqadm space upsert -f backup.yaml --slot prod --target space_dst456
uqadm space upsert -f backup.yaml --dry-run
```

| Option | Description |
|--------|-------------|
| `-f`, `--file FILE` | Local snapshot (`.json`, `.yaml`, or `.yml`). Required. |
| `--slot SLOT` | Credential slot (default: configured default slot). |
| `--target SPACE_ID` | Space id or URL to update. Omit to create a new space. |
| `--dry-run` | Print actions without calling create/update APIs. |

### `space diff`

Compare two spaces. Exits **0** if identical, **1** if differences exist.

```bash
uqadm space diff --source "qa:space_a" --destination "qa:space_b"
uqadm space diff --source "qa:space_x" --destination "prod:space_y" --format side-by-side
uqadm space diff --source "qa:x" --destination "prod:y" --strict
```

| Option | Description |
|--------|-------------|
| `--source SPEC` | First space (`slot:space_id` or `slot:URL`). |
| `--destination SPEC` | Second space (same format). |
| `--strict` | Compare raw payloads (skip normalization). |
| `--format` | `unified` (default) or `side-by-side`. |

By default, ephemeral keys (`id`, `createdAt`, `updatedAt`, etc.) are stripped before comparison so you see meaningful config drift.

### `space migrate`

Copy assistant configuration from a source space to a destination (new or existing).

```bash
uqadm space migrate --source "qa:space_src123" --destination "prod:"          # create new
uqadm space migrate --source "qa:space_src123" --destination "prod:space_dst" # update existing
uqadm space migrate --source "qa:space_src123" --destination "prod:" --dry-run
```

| Option | Description |
|--------|-------------|
| `--source SPEC` | Source space (`slot:space_id` or `slot:URL`). Space id required. |
| `--destination SPEC` | `slot` / `slot:` to create; `slot:space_id` or `slot:URL` to update. |
| `--dry-run` | Print actions without making API write calls. |
| `--with-knowledge` | Reserved; currently informational only. |

**Endpoint spec format** (`slot:space_id` or `slot:URL`):

| Spec | Slot | Space id |
|------|------|----------|
| `qa` | `qa` | *(none — create)* |
| `qa:` | `qa` | *(none — create)* |
| `qa:space_abc123` | `qa` | `space_abc123` |
| `prod:https://host/app/space/space_xyz` | `prod` | `space_xyz` |

Supported URL path markers: `/space/<id>`, `/custom-space/<id>`, `/swappable-intelligence-space/<id>`.

### `space access-grant SPACE_ID`

Add **user or group** entries to a space ACL via ``Space.add_space_access``. The API **merges** new entries with existing access; it does not replace the full ACL.

```bash
uqadm space access-grant asst_abc --group grp_1 --group grp_2
uqadm space access-grant asst_abc --user user_1 --type MANAGE --slot qa
```

| Option | Description |
|--------|-------------|
| `SPACE_ID` | Space id or URL (same rules as ``space export``). |
| `--group ID` | Repeat for each group. |
| `--user ID` | Repeat for each user. |
| `--type` | `USE` (default), `MANAGE`, or `UPLOAD`. |
| `--slot SLOT` | Credential slot (default: configured default). |

### `space ingestion-set SPACE_ID CONFIG_FILE`

Load a JSON/YAML **mapping** from disk and assign it to **``settings.ingestionConfig``** on the assistant. Other top-level ``settings`` keys are preserved (shallow merge); the file content **replaces** the previous ``ingestionConfig`` object.

Folder-level ingestion (knowledge base) uses a different shape; use ``uqadm kb ingestion set`` for scopes/folders.

```bash
uqadm space ingestion-set asst_abc ./ingestion.json
uqadm space ingestion-set asst_abc ./ingestion.yaml --slot prod --dry-run
```

| Option | Description |
|--------|-------------|
| `CONFIG_FILE` | ``.json``, ``.yaml``, or ``.yml``; root must be a mapping. |
| `--dry-run` | Print which ``settings`` keys would be sent without PATCHing. |
| `--slot SLOT` | Credential slot (default: configured default). |

### `space delete SPACE_ID`

Delete a space (prompts for confirmation unless `-y`).

```bash
uqadm space delete space_old123
uqadm space delete space_old123 --slot prod -y
uqadm space delete space_old123 --dry-run
```

| Option | Description |
|--------|-------------|
| `SPACE_ID` | Space id or `https://` URL containing `/space/<id>`. |
| `--slot SLOT` | Credential slot (default: configured default slot). |
| `-y`, `--yes` | Skip the confirmation prompt. |
| `--dry-run` | Fetch and describe what would be deleted, without deleting. |

---

## `uqadm kb`

Manage **knowledge-base folder** paths and metadata via ``unique_sdk.Folder``.

```bash
uqadm kb --help
```

### `kb mkdir`

Create one or more folder paths. Pass paths as arguments, with ``--path`` (repeatable), and/or ``--paths-file`` (one path per line; ``#`` starts a comment). Use ``--parent-scope-id`` with relative path segments instead of absolute ``paths``.

```bash
uqadm kb mkdir /Dept/HR /Dept/Legal
uqadm kb mkdir --paths-file folders.txt --slot qa
uqadm kb mkdir rel/sub --parent-scope-id scope_parent123
uqadm kb mkdir /Private --no-inherit-access
```

| Option | Description |
|--------|-------------|
| `--paths-file` | Text file of paths (one per line). |
| `--path` | Single path (repeatable). |
| `--parent-scope-id` | Use ``relativePaths`` under this scope. |
| `--inherit-access / --no-inherit-access` | Passed to ``Folder.create_paths`` (default: inherit). |
| `--slot SLOT` | Credential slot. |

### `kb sync`

Upload the contents of a local folder into a KB folder scope. Files matched by
filename are **replaced**; new files are **created**. This is an **upsert, not a
destructive mirror**: files that exist in the upstream KB scope but are missing
locally are **left untouched — `kb sync` never deletes remote files**. Requires
exactly one of ``--folder-path`` or ``--scope-id``. Without ``--recursive`` only
top-level files are synced; with it, subdirectories are recreated as child folders.

```bash
uqadm kb sync ./docs --folder-path /Dept/HR
uqadm kb sync ./docs --folder-path /Dept/HR -r --dry-run
uqadm kb sync ./docs --scope-id scope_abc -r --slot qa
```

| Option | Description |
|--------|-------------|
| `--folder-path` | Target KB folder path (mutually exclusive with ``--scope-id``). |
| `--scope-id` | Target folder scope id (mutually exclusive with ``--folder-path``). |
| `-r`, `--recursive` | Recurse into subdirectories, mirroring them as child KB folders. |
| `--dry-run` | Show planned uploads without writing anything. |
| `--slot SLOT` | Credential slot. |

Extensions that the OS `mimetypes` database cannot resolve (common on macOS for
``.md``, ``.xsd``, etc.) are mapped to curated text/doc MIME types; anything
still unknown is uploaded as ``application/octet-stream`` with a stderr warning
instead of failing the sync.

### `kb access grant`

Grant **group** ``READ`` or ``WRITE`` on a folder. By default the change **applies to subfolders** (``applyToSubScopes``); pass ``--no-subfolders`` for this folder only.

```bash
uqadm kb access grant --folder-path /Dept/HR --group grp_1 --permission READ
uqadm kb access grant --scope-id scope_abc --group grp_1 --group grp_2 --permission WRITE --no-subfolders
```

### `kb ingestion set CONFIG_FILE`

Apply **folder** ingestion settings from a JSON/YAML file (mapping root) using ``Folder.update_ingestion_config``. Default applies to **subfolders**; use ``--no-subfolders`` for this folder only.

```bash
uqadm kb ingestion set ./folder-ingest.json --folder-path /Dept/HR
uqadm kb ingestion set ./ingest.yaml --scope-id scope_abc --slot qa
```

---

## `uqadm chat`

Send messages to an assistant and inspect conversation history.

```bash
uqadm chat --help
```

### `chat send ASSISTANT_ID`

Send a message and print the reply. The `chat_id` of the thread is always shown in the framed header so you can copy it for follow-up messages.

**Message input** (pick one):

| Method | Flag / Usage |
|--------|-------------|
| Inline text | `--text "your message"` |
| File | `--file ./prompt.txt` |
| stdin | `echo "message" \| uqadm chat send ASSISTANT_ID` |

**Output format:**

```
────────────────────────────────────────────────────────────
chat_id: chat_xyz789
────────────────────────────────────────────────────────────
Here are the latest F1 headlines...
────────────────────────────────────────────────────────────
References
  [1] Formula 1 Official  https://www.formula1.com/...
────────────────────────────────────────────────────────────
Evaluation
  APPROVED · accurate
  The answer correctly summarizes recent race results.
────────────────────────────────────────────────────────────
```

References and Evaluation sections only appear when the response includes them. Use `--json` to get the full raw `Space.Message` object instead.

**Examples:**

```bash
# First message — starts a new thread
uqadm chat send asst_abc123 --text "What are the latest F1 news?"

# Follow-up in the same thread
uqadm chat send asst_abc123 --text "Tell me more about the race" --chat-id chat_xyz789

# Specific slot
uqadm chat send asst_abc123 --text "Hello" --slot prod

# Force a tool
uqadm chat send asst_abc123 --text "Search the web" --tool web_search

# Force multiple tools
uqadm chat send asst_abc123 --text "Run and explain" --tool code_interpreter --tool web_search

# Message from a file
uqadm chat send asst_abc123 --file ./prompt.txt

# Piped from stdin
echo "Summarize this" | uqadm chat send asst_abc123

# Increase timeout (default: 300 s)
uqadm chat send asst_abc123 --text "Complex question" --max-wait 600

# Raw JSON output
uqadm chat send asst_abc123 --text "Hello" --json
```

**All options:**

| Option | Default | Description |
|--------|---------|-------------|
| `ASSISTANT_ID` | — | The assistant to message. |
| `--slot SLOT` | default slot | Credential slot. |
| `--text TEXT` | — | Inline message text. |
| `--file PATH` | — | Read message from file. |
| `--chat-id ID` | — | Continue an existing chat thread. |
| `--tool NAME` | — | Force a tool (repeatable). |
| `--max-wait SECS` | `300` | Timeout waiting for a response. |
| `--poll-interval SECS` | `1.0` | Polling interval between status checks. |
| `--stop-on` | `stoppedStreamingAt` | Stop condition: `stoppedStreamingAt` or `completedAt`. |
| `--json` | off | Print raw `Space.Message` JSON. |

### `chat history CHAT_ID`

Fetch and display conversation history.

By default, shows the **selected token window** (last N messages within a token budget) — useful for reviewing context. Use `--full` to see every message in the thread exactly as stored.

```bash
uqadm chat history chat_xyz789
uqadm chat history chat_xyz789 --full
uqadm chat history chat_xyz789 --full --json
uqadm chat history chat_xyz789 --slot prod
```

Output uses the same framed style as `chat send`, with each message in its own block labeled `You` or `Assistant`.

| Option | Default | Description |
|--------|---------|-------------|
| `CHAT_ID` | — | Chat thread to fetch. |
| `--slot SLOT` | default slot | Credential slot. |
| `--full` | off | Show all messages (bypasses token-window selection). |
| `--json` | off | Print raw message list as JSON. |
| `--max-tokens INT` | `8000` | Token budget for the windowed view. |
| `--percent FLOAT` | `0.15` | Fraction of `max-tokens` allocated to history. |
| `--max-messages INT` | `4` | Maximum number of messages in the windowed view. |

---

## Python module entry

```bash
python -m uqadm --help
```

---

## Related

- **`unique-cli`** — SDK file-explorer CLI (`unique_sdk`); unchanged by `uqadm`.
- **`unique_sdk.cli.config`** — `load_config()` and env semantics shared with `unique-cli`.
