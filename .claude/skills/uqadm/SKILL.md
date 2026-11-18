---
name: uqadm
description: Administer Unique AI spaces and knowledge bases with the uqadm CLI. Use when the user asks to export, upsert, migrate, clone, diff or delete a space; copy space configuration between environments or credential slots (qa/prod); push config to an existing space without changing its access rights; replace a language model across spaces or ingestion configs; grant space or folder access; or create, sync, download or remove knowledge-base folders and files.
license: MIT
compatibility: claude cursor opencode
metadata:
  version: "1.0.0"
  languages: bash
  audience: admins, developers
  workflow: operations
  since: "2026-11-18"
---

## What I do

Turn space and knowledge-base admin requests into safe `uqadm` command
sequences: preview with `--dry-run`, apply, then verify. I know which data each
command does and doesn't copy, so I don't promise things the CLI can't do,
such as scope rules.

Full reference: [`uqadm/README.md`](../../../uqadm/README.md). Run
`uqadm <group> <command> --help` for the current flags before using an
unfamiliar option.

## Setup and credential slots

```bash
uv sync --package uqadm            # from the ai repo root (or: pip install -e uqadm/)
uqadm install                      # dirs, shell completion, first slot
uqadm env create qa
uqadm env create prod --set-default
uqadm env list                     # shows all slots; * marks the default
uqadm env show prod                # resolved credentials for one slot
```

- Single-slot commands take `--slot SLOT`, which loads `~/.uqadm/envs/.{SLOT}.env`. Without it, the default slot is used.
- **`space migrate` and `space diff` don't accept `--slot`.** They pick a slot per side from **endpoint specs**: `slot:space_id` or `slot:https://host/.../space/<id>`. For `migrate --destination`, a bare `slot` or `slot:` means *create a new space*.
- Single-space commands accept a bare id or a space URL.

## Command map

| Group | Command | Purpose |
|-------|---------|---------|
| space | `list [--name X] [--json]` | List spaces in a slot. |
| space | `export ID [-o f.yaml] [--no-access]` | Snapshot to stdout (JSON) or file. |
| space | `upsert -f FILE [--target ID]` | Create (no `--target`) or update a space from a snapshot. |
| space | `migrate --source S --destination D` | Copy config space-to-space, including across slots. |
| space | `diff --source S --destination D [--strict] [--ignore-access]` | Exit 0 = same, 1 = different. |
| space | `model-replace [ID \| -f FILE \| --all] --from-model A --to-model B` | Swap the LLM in fields, modules, and the model list. |
| space | `access-grant ID --group G / --user U [--type USE\|MANAGE\|UPLOAD]` | Add ACL entries (merged with existing ones). |
| space | `ingestion-set ID FILE` | Replace `settings.ingestionConfig`. |
| space | `delete ID [-y]` | Delete a space (**can't be undone**). |
| kb | `mkdir PATH... [--no-inherit-access]` | Create folder paths. |
| kb | `sync DIR --folder-path P [-r] [--no-version] [--no-inherit-access]` | Upload/replace files by name; never deletes remote files. |
| kb | `download DIR --folder-path P [-r]` | Download folder contents. |
| kb | `rm --folder-path P [--file F] [-r] [-y]` | Delete folders/files (**can't be undone**). |
| kb | `access grant --folder-path P --group G --permission READ\|WRITE` | Grant folder access (applies to subfolders by default). |
| kb | `ingestion get / set / model-replace` | Read/write a folder's ingestion config. |
| chat | `send ID --text "..." [--chat-id C]`, `history CHAT_ID` | Talk to an assistant. |

## What upsert / migrate copy

| Item | Behaviour |
|------|-----------|
| Space fields, settings, prompts, model switching, sub-agent settings | Copied. |
| Modules | On update: matched **by name**; unmatched source modules are skipped (warning). On create: all are created. |
| Module configuration (incl. knowledge `scopeIds`) | Copied verbatim. **Scope ids don't carry over to another environment**, so check them after a cross-env run. |
| Access (`assistantAccess`) | **Merged**: source entries are added, existing ones are never removed. `--no-access` skips the merge. |
| Scope rules | **Never applied.** There's no public write API. Tell the user to set them manually in the UI. |
| MCP bindings | Top-level `assistantMcpServers` only with `--with-mcp-servers`. `migrate` ignores the flag across environments. Servers already on the destination aren't removed. MCP tool entries *inside module configuration* are copied with the module config, whatever the flag. |

## Recipes

**Push config to an existing space without touching its access rights**

```bash
set -euo pipefail                      # stop on the first failed export/extraction
command -v jq >/dev/null || { echo "jq is required" >&2; exit 1; }
WORK=$(mktemp -d)                      # fresh paths: never compare a stale snapshot

# Capture and validate the baseline BEFORE any write. jq -e fails unless the
# field is a real array, so a bad baseline stops the recipe early.
uqadm space export DST --slot prod -o "$WORK/before.json"
jq -eS '.assistantAccess | arrays' "$WORK/before.json" > "$WORK/acl-before.json"

uqadm space migrate --source qa:SRC --destination prod:DST --no-access --dry-run
uqadm space migrate --source qa:SRC --destination prod:DST --no-access

uqadm space export DST --slot prod -o "$WORK/after.json"
jq -eS '.assistantAccess | arrays' "$WORK/after.json"  > "$WORK/acl-after.json"
diff "$WORK/acl-before.json" "$WORK/acl-after.json" && echo "ACL unchanged"

uqadm space diff --source qa:SRC --destination prod:DST --ignore-access   # config-only comparison
```

`diff --ignore-access` compares source and destination *configuration*. It
can't tell you whether the destination ACL changed; use the before/after
exports for that. Only report "ACL unchanged" when both `jq -e` extractions
succeeded.

Reviewable alternative using a snapshot file:

```bash
uqadm space export SRC --slot qa -o space.yaml --no-access
# review / edit space.yaml
uqadm space upsert -f space.yaml --slot prod --target DST --dry-run
uqadm space upsert -f space.yaml --slot prod --target DST
```

**Clone into a brand-new space**: `uqadm space migrate --source qa:SRC --destination prod:`.
Add `--no-access` if the source's groups don't exist in the target environment.

**Back up before changes**:

```bash
mkdir -p backups
# Unique per run (timestamp + PID); refuse to overwrite an existing backup.
BACKUP="backups/ID-$(date +%Y%m%dT%H%M%S)-$$.yaml"
[ ! -e "$BACKUP" ] || { echo "refusing to overwrite $BACKUP" >&2; exit 1; }
# Only report a backup that was actually written; stop before any change otherwise.
uqadm space export ID --slot prod -o "$BACKUP" && [ -s "$BACKUP" ] \
  || { echo "backup FAILED; do not proceed" >&2; exit 1; }
echo "Backup: $BACKUP"                 # record this path; reapply exactly this file

# later, to reapply the saved configuration to the same space on the same slot:
uqadm space upsert -f "$BACKUP" --slot prod --target ID --dry-run
uqadm space upsert -f "$BACKUP" --slot prod --target ID
```

If the backup has top-level `assistantMcpServers` you want restored, add
`--with-mcp-servers` to **both** the dry run and the write, on the original slot.
Without the flag those bindings are skipped (with only a stderr warning). MCP
tool entries *inside module configuration* are restored with the module config
whatever the flag. Reapplying a binding doesn't remove bindings added after the
backup.

This **isn't a full rollback**. Upsert reapplies the supported configuration
fields and only *adds* saved access entries. It doesn't revoke access granted
after the backup, remove modules or MCP bindings added since, or restore scope
rules. Recover those separately, for example by revoking access in the UI.

**Model rollout**: preview with `uqadm space model-replace --all --slot prod --from-model OLD --to-model NEW --dry-run`,
then do the same for `uqadm kb ingestion model-replace --all ...`.

**Sync docs to a new restricted folder**:
`uqadm kb sync ./docs --folder-path /Private/New -r --no-inherit-access`, then
`uqadm kb access grant --folder-path /Private/New --group G --permission READ`.

## Safety rules

1. Run `--dry-run` first for upsert, migrate, ingestion-set, model-replace, delete, kb sync, and kb rm.
2. Before a cross-slot write, confirm the destination slot (`uqadm env show SLOT`). Prod writes affect real users.
3. Never run `space delete` or `kb rm` without explicit user confirmation. Use `-y` only when the user asked for it.
4. When the user cares about ACLs, export the **same destination on the same slot** before and after the write and compare `assistantAccess` (see the recipe above). `space diff` compares two live spaces and can't show a space's earlier state.
5. Treat warnings on stderr (unmatched modules, scope rules, MCP bindings) as action items for the user. Don't drop them silently.
6. On auth errors, `uqadm env show SLOT` prints the resolved credentials so you can debug the slot.
