---
name: unique-cli-file-management
description: >-
  Manage files and folders on the Unique AI Platform using the unique-cli
  command-line tool. Use when the user asks to upload, download, delete,
  rename, list, find, look for, or organize files and folders on Unique,
  or when working with scope IDs (scope_*) or content IDs (cont_*).
  IMPORTANT: When a user says they are "looking for a file" or wants to
  "find a file", they typically mean locating it within the Unique AI
  Platform knowledge base — not on the local filesystem. Use this skill
  to browse and list folders/files on Unique to help them find it.
  This is also the preferred approach for locating Excel (.xlsx/.xls),
  CSV (.csv), and image files, as these file types are not full-text
  indexed and cannot be found via vector/full-text search.
---

# Unique CLI -- File & Folder Management

`unique-cli` is a Linux-like file explorer for the Unique AI Platform knowledge base.
It is installed via `pip install unique-sdk` and requires these environment variables:

```bash
UNIQUE_USER_ID    # User ID (required)
UNIQUE_COMPANY_ID # Company ID (required)
UNIQUE_API_KEY    # API key — optional on localhost / secured cluster
UNIQUE_APP_ID     # App ID — optional on localhost / secured cluster
```

## One-Shot Commands

Run commands directly from the shell without entering the interactive mode:

```bash
# List root folders
unique-cli ls

# List a specific folder
unique-cli ls /Reports/Q1

# List by scope ID
unique-cli ls scope_abc123

# Create a folder
unique-cli mkdir Q2

# Delete a folder (use -r for non-empty)
unique-cli rmdir /Reports/Q2
unique-cli rmdir scope_abc123 -r

# Rename a folder
unique-cli mvdir Q1 "Q1-2025"

# Upload a file (to current scope -- cd first or specify destination)
unique-cli upload ./report.pdf
unique-cli upload ./report.pdf /Reports/Q1/
unique-cli upload ./data.csv scope_abc123

# Download a file
unique-cli download report.pdf ./local/
unique-cli download cont_abc123 ~/Desktop/

# Delete a file
unique-cli rm report.pdf
unique-cli rm cont_abc123

# Rename a file
unique-cli mv report.pdf "Annual Report 2025.pdf"
```

## Path & ID Formats

| Format | Example | Resolves to |
|--------|---------|-------------|
| Relative name | `Reports` | Child of current directory |
| Absolute path | `/Company/Reports/Q1` | From root |
| Scope ID | `scope_abc123` | Folder directly by ID |
| `..` | `..` | Parent directory |
| `/` | `/` | Root |
| Content ID | `cont_abc123` | File directly by ID |

## Upload Destination Resolution

The `upload` destination works like Linux `cp`:

| Destination | Behavior |
|-------------|----------|
| *(omitted)* or `.` | Current folder, keep filename |
| `newname.pdf` | Current folder, rename |
| `subfolder/` | Into subfolder, keep filename |
| `/abs/path/` | Into absolute path folder |
| `scope_abc123` | Into that scope ID |
| `sub/new.pdf` | Into sub, renamed |

## Common Workflows

### Upload multiple files to a folder

```bash
for f in ./documents/*.pdf; do
  unique-cli upload "$f" /Reports/2025/
done
```

### List and download all files from a folder

```bash
# First list to see what's there
unique-cli ls /Reports/Q1

# Download specific files
unique-cli download "annual.pdf" ./downloads/
unique-cli download cont_abc123 ./downloads/
```

### Create folder hierarchy and upload

```bash
unique-cli mkdir "2025/Q1/Financials"
unique-cli upload ./budget.xlsx /2025/Q1/Financials/
```

## Error Handling

- If env vars are missing, the CLI exits with a clear error listing the missing variables.
- File-not-found and folder-not-found errors are returned as text, not exceptions.
- All commands print their result to stdout -- parse output as needed.

## Interactive Mode

For multiple operations, use the interactive shell:

```bash
unique-cli
```

This opens a REPL with the same commands (without the `unique-cli` prefix). Type `help` for a list or `exit` to quit.
