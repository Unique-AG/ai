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
uqadm env create prod --set-default
uqadm env list | uqadm env show prod | uqadm env set-default qa
```

- Every command takes `--slot SLOT`, which loads `~/.uqadm/envs/.{SLOT}.env`. Without it, the default slot is used.
- Commands that take two spaces use **endpoint specs**: `slot:space_id` or `slot:https://host/.../space/<id>`. For `migrate --destination`, a bare `slot` or `slot:` means *create a new space*.
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
| MCP bindings | Only with `--with-mcp-servers`. `migrate` ignores the flag across environments. Servers already on the destination aren't removed. |

## Recipes

**Push config to an existing space without touching its access rights**

```bash
uqadm space migrate --source qa:SRC --destination prod:DST --no-access --dry-run
uqadm space migrate --source qa:SRC --destination prod:DST --no-access
uqadm space diff --source qa:SRC --destination prod:DST --ignore-access
```

Reviewable alternative using a snapshot file:

```bash
uqadm space export SRC --slot qa -o space.yaml --no-access
# review / edit space.yaml
uqadm space upsert -f space.yaml --slot prod --target DST --dry-run
uqadm space upsert -f space.yaml --slot prod --target DST
```

**Clone into a brand-new space**: `uqadm space migrate --source qa:SRC --destination prod:`.
Add `--no-access` if the source's groups don't exist in the target environment.

**Back up before changes**: `uqadm space export ID --slot prod -o backup-$(date +%F).yaml`.
To restore, run `upsert -f backup.yaml --target ID`.

**Model rollout**: preview with `uqadm space model-replace --all --slot prod --from-model OLD --to-model NEW --dry-run`,
then do the same for `uqadm kb ingestion model-replace --all ...`.

**Sync docs to a new restricted folder**:
`uqadm kb sync ./docs --folder-path /Private/New -r --no-inherit-access`, then
`uqadm kb access grant --folder-path /Private/New --group G --permission READ`.

## Safety rules

1. Run `--dry-run` first for upsert, migrate, ingestion-set, model-replace, delete, kb sync, and kb rm.
2. Before a cross-slot write, confirm the destination slot (`uqadm env show SLOT`). Prod writes affect real users.
3. Never run `space delete` or `kb rm` without explicit user confirmation. Use `-y` only when the user asked for it.
4. When the user cares about ACLs, compare `uqadm space export ID -o before.json` with an export taken afterwards, or run `diff --strict` without `--ignore-access`.
5. Treat warnings on stderr (unmatched modules, scope rules, MCP bindings) as action items for the user. Don't drop them silently.
6. On auth errors, `uqadm env show SLOT` prints the resolved credentials so you can debug the slot.
