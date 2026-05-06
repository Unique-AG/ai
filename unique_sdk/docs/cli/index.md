# Unique CLI

!!! warning "Experimental"
    The CLI is experimental and its interface may change in future releases.

Unique CLI is a Linux-like interactive file explorer for the Unique AI Platform. It provides familiar commands (`cd`, `ls`, `mkdir`, `rm`, `mv`, etc.) to browse, manage, and search files and folders stored in the Unique knowledge base -- as if you were connected to a remote server via SSH.

## Two Modes of Operation

### Interactive Shell

Run `unique-cli` without arguments to enter the interactive shell. You get a prompt showing your current directory and can type commands just like a terminal:

```
$ unique-cli
Unique File System v0.1.0
Connected as user_abc @ company_xyz
Type 'help' for available commands.

/> ls
DIR   Reports/           scope_abc123               2025-03-01 10:00
DIR   Projects/          scope_def456               2025-02-15 14:30
FILE  readme.txt         cont_ghi789      1.2 KB    2025-03-10 09:00

/> cd Reports
/Reports> ls
DIR   Q1/                scope_jkl012               2025-01-15 08:00
FILE  annual.pdf         cont_mno345      5.4 MB    2025-03-01 12:00

/Reports> search "revenue growth" --limit 50
Found 12 result(s):

    1. annual.pdf (p.5-6)  [cont_mno345]
       ...revenue growth exceeded expectations in Q4...

/Reports> exit
```

### One-Shot Commands

Run any command directly from your terminal without entering the shell:

```bash
# List root folders
unique-cli ls

# List a specific folder
unique-cli ls /Reports/Q1

# Create a folder
unique-cli mkdir /Reports/Q2

# Upload a file
unique-cli upload ./local-report.pdf

# Search across everything
unique-cli search "quarterly earnings" --limit 50

# Download by content ID
unique-cli download cont_abc123 ./downloads/
```

## Quick Start

### 1. Install

The CLI ships with the SDK. Install from [PyPI](https://pypi.org/project/unique-sdk/):

```bash
pip install unique-sdk
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv pip install unique-sdk
```

### 2. Configure

Set the required environment variables:

```bash
export UNIQUE_API_KEY="ukey_..."
export UNIQUE_APP_ID="app_..."
export UNIQUE_USER_ID="user_..."
export UNIQUE_COMPANY_ID="company_..."
```

Optionally override the API base URL (defaults to `https://gateway.unique.app/public/chat-gen2`):

```bash
export UNIQUE_API_BASE="https://custom-gateway.example.com/public/chat-gen2"
```

### 3. Run

```bash
# Interactive shell
unique-cli

# Or one-shot
unique-cli ls /
```

You can also run the CLI as a Python module:

```bash
python -m unique_sdk.cli
```

## Command Overview

| Command | Description | Example |
|---------|-------------|---------|
| `pwd` | Print current directory | `pwd` |
| `cd` | Change directory | `cd /Reports`, `cd ..`, `cd scope_abc` |
| `ls` | List files and folders | `ls`, `ls /Reports` |
| `mkdir` | Create a folder | `mkdir Q2` |
| `rmdir` | Delete a folder | `rmdir Q2`, `rmdir Q2 -r` |
| `mvdir` | Rename a folder | `mvdir OldName NewName` |
| `upload` | Upload a local file | `upload ./report.pdf` |
| `download` | Download a file | `download report.pdf ./local/` |
| `rm` | Delete a file | `rm report.pdf` |
| `mv` | Rename a file | `mv old.pdf new.pdf` |
| `search` | Combined search | `search "query" --folder /Reports` |
| `mcp` | Call an MCP server tool by name | `mcp -c chat_1 -m msg_1 '{"name":"tool","arguments":{}}'` |
| `schedule` | Manage scheduled tasks | `schedule list`, `schedule create ...` |
| `elicit` | Ask the user a question and read the answer | `elicit ask "Which quarter?"` |
| `help` | Show available commands | `help`, `help search` |
| `exit` | Exit the shell | `exit` |

## Path Resolution

All commands that accept a path support three formats:

- **Relative name**: `Reports` -- resolved relative to the current directory
- **Absolute path**: `/Company/Reports/Q1` -- resolved from root
- **Scope ID**: `scope_abc123` -- used directly as the folder identifier

Files can be referenced by:

- **File name**: `report.pdf` -- matched against files in the current directory
- **Content ID**: `cont_abc123` -- used directly as the file identifier

## Next Steps

- [Command Reference](commands.md) -- detailed documentation for every command
- [Scheduled Tasks](scheduled_tasks.md) -- create and manage recurring cron-based tasks
- [Elicitation](elicitation.md) -- ask the user structured questions and read typed answers
- [Search Guide](search.md) -- how to use combined search with metadata filters
- [Configuration](configuration.md) -- environment variables and setup details
