# Command Reference

!!! warning "Experimental"
    The CLI is experimental and its interface may change in future releases.

This page documents every command available in Unique CLI, both in the interactive shell and as one-shot subcommands.

## Navigation

### pwd

Print the current working directory path.

**Interactive shell:**

```
/Reports> pwd
/Reports
```

**One-shot:**

```bash
unique-cli pwd
```

The CLI tracks your position in the Unique folder hierarchy. At startup, you begin at `/` (root). The path shown is the human-readable folder path, not the scope ID.

---

### cd

Change the current working directory.

**Synopsis:**

```
cd <target>
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `target` | Folder name, absolute path, scope ID, `..` for parent, or `/` for root |

**Examples:**

```
/> cd Reports
/Reports>

/Reports> cd Q1
/Reports/Q1>

/Reports/Q1> cd ..
/Reports>

/Reports> cd /
/>

/> cd scope_abc123
/Company/Reports>
```

**Path resolution rules:**

- A plain name like `Reports` is resolved relative to the current directory
- A path starting with `/` is treated as absolute: `/Company/Reports/Q1`
- `..` navigates to the parent directory
- `/` navigates to the root
- A string starting with `scope_` is treated as a scope ID and resolved directly

If the target folder does not exist, an error is shown and the directory is unchanged.

---

### ls

List folders and files in the current (or specified) directory.

**Synopsis:**

```
ls [target]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `target` | Optional. Folder name, absolute path, or scope ID to list. Defaults to current directory. |

**Output format:**

```
/Reports> ls
DIR   Q1/                scope_jkl012               2025-01-15 08:00
DIR   Q2/                scope_pqr678               2025-04-01 10:30
FILE  annual.pdf         cont_mno345      5.4 MB    2025-03-01 12:00
FILE  summary.docx       cont_xyz789      128 KB    2025-03-10 09:15
2 folder(s), 2 file(s)
```

Each line shows:

| Column | Description |
|--------|-------------|
| Type | `DIR` for folders, `FILE` for files |
| Name | Folder name (with trailing `/`) or file title |
| ID | Scope ID for folders, content ID for files |
| Size | File size (human-readable). Empty for folders. |
| Updated | Last modification date |

The summary line at the bottom shows total counts.

**One-shot examples:**

```bash
# List root
unique-cli ls

# List a specific path
unique-cli ls /Reports/Q1

# List by scope ID
unique-cli ls scope_abc123
```

---

## Folder Operations

### mkdir

Create a new folder under the current directory.

**Synopsis:**

```
mkdir <name>
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `name` | Name of the folder to create |

**Examples:**

```
/Reports> mkdir Q2
Created: /Reports/Q2 (scope_pqr678)
```

The folder is created as a child of the current directory. Nested paths in a single `mkdir` are supported by the underlying API (e.g., `mkdir "A/B/C"` creates the full hierarchy).

**One-shot:**

```bash
unique-cli mkdir Q2
```

---

### rmdir

Delete a folder.

**Synopsis:**

```
rmdir <target> [--recursive|-r]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `target` | Folder name, absolute path, or scope ID |

**Options:**

| Option | Description |
|--------|-------------|
| `--recursive`, `-r` | Delete the folder and all its contents (subfolders and files) |

**Examples:**

```
/Reports> rmdir Q2
Deleted folder: /Reports/Q2

/Reports> rmdir Q1 --recursive
Deleted folder: /Reports/Q1
```

Without `--recursive`, deleting a non-empty folder will fail. Use `-r` to force deletion of everything inside.

**One-shot:**

```bash
unique-cli rmdir /Reports/Q2
unique-cli rmdir scope_abc123 --recursive
```

---

### mvdir

Rename a folder.

**Synopsis:**

```
mvdir <old_name> <new_name>
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `old_name` | Current folder name, path, or scope ID |
| `new_name` | New name for the folder |

**Examples:**

```
/Reports> mvdir Q1 "Q1-2025"
Renamed folder -> Q1-2025
ID:       scope_jkl012
Name:     Q1-2025
Parent:   scope_abc123
Created:  2025-01-15 08:00
Updated:  2025-03-19 14:30
```

This renames the folder without moving it. The folder stays in the same parent directory.

**One-shot:**

```bash
unique-cli mvdir Q1 "Q1-2025"
unique-cli mvdir scope_abc123 "New Name"
```

---

## File Operations

### upload

Upload a local file to the Unique platform. The destination argument works like the target in Linux `cp`.

**Synopsis:**

```
upload <local_path> [destination]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `local_path` | Path to the local file to upload |
| `destination` | Optional. Where and how to upload (see formats below). Defaults to current directory with original filename. |

**Destination formats:**

| Format | Behavior |
|--------|----------|
| *(omitted)* | Upload to current directory, keep original filename |
| `.` | Upload to current directory, keep original filename |
| `newname.pdf` | Upload to current directory, rename to `newname.pdf` |
| `subfolder/` | Upload into subfolder (trailing `/`), keep original filename |
| `./subfolder/` | Same as above, relative to current directory |
| `subfolder/newname.pdf` | Upload into subfolder with new name |
| `/absolute/path/` | Upload into absolute folder path, keep original filename |
| `scope_abc123` | Upload into that scope ID, keep original filename |

**Examples:**

```
/Reports> upload ./quarterly-report.pdf
Uploaded: quarterly-report.pdf (cont_stu901) to /Reports

/Reports> upload ~/data/raw.csv "Q1 Data Export.csv"
Uploaded: Q1 Data Export.csv (cont_vwx234) to /Reports

/Reports> upload ./report.pdf Q1/
Uploaded: report.pdf (cont_xyz) to /Reports/Q1

/Reports> upload ./report.pdf /Archive/2025/
Uploaded: report.pdf (cont_abc) to /Archive/2025
```

The MIME type is auto-detected from the file extension.

**One-shot:**

```bash
unique-cli upload ./report.pdf
unique-cli upload ./report.pdf "Clean Report.pdf"
unique-cli upload ./data.csv Q1/
unique-cli upload ./data.csv /Archive/2025/
```

---

### download

Download a file from the Unique platform to your local machine.

**Synopsis:**

```
download <name_or_id> [local_path]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `name_or_id` | File name (matched in the current directory) or content ID (`cont_...`) |
| `local_path` | Optional. Local directory or file path to save to. Defaults to the current working directory. |

**Examples:**

```
/Reports> download annual.pdf
Downloaded: annual.pdf -> /Users/me/annual.pdf

/Reports> download annual.pdf ./downloads/
Downloaded: annual.pdf -> /Users/me/downloads/annual.pdf

/Reports> download cont_mno345 ~/Desktop/
Downloaded: cont_mno345 -> /Users/me/Desktop/cont_mno345
```

When downloading by name, the file is looked up among the files in the current directory. When downloading by content ID (`cont_...`), the ID is used directly regardless of the current directory.

**One-shot:**

```bash
unique-cli download annual.pdf ./local/
unique-cli download cont_abc123 ~/Desktop/
```

---

### rm

Delete a file.

**Synopsis:**

```
rm <name_or_id>
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `name_or_id` | File name (matched in the current directory) or content ID (`cont_...`) |

**Examples:**

```
/Reports> rm annual.pdf
Deleted: annual.pdf (cont_mno345)

/Reports> rm cont_xyz789
Deleted: cont_xyz789 (cont_xyz789)
```

**One-shot:**

```bash
unique-cli rm annual.pdf
unique-cli rm cont_abc123
```

---

### mv

Rename a file.

**Synopsis:**

```
mv <old_name> <new_name>
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `old_name` | Current file name or content ID |
| `new_name` | New title for the file |

**Examples:**

```
/Reports> mv annual.pdf annual-2025.pdf
Renamed: annual.pdf -> annual-2025.pdf
ID:       cont_mno345
Title:    annual-2025.pdf
MIME:     application/pdf
Size:     5.4 MB
Owner:    user_123
Created:  2025-01-15 08:00
Updated:  2025-03-19 14:30
```

This changes the file's display title. The content ID remains the same.

**One-shot:**

```bash
unique-cli mv annual.pdf annual-2025.pdf
unique-cli mv cont_abc123 "New Title.pdf"
```

---

## Search

### search

Search the knowledge base using combined (vector + full-text) search.

**Synopsis:**

```
search <query> [--folder <path|scope_id>] [--metadata <key=value>] [--limit <N>]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `query` | The search query text |

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--folder`, `-f` | Restrict search to a folder (by path, name, or scope ID) | Current directory |
| `--metadata`, `-m` | Filter by metadata as `key=value`. Can be repeated. | None |
| `--limit`, `-l` | Maximum number of results | 200 |

**Examples:**

```
/Reports> search "revenue growth"
Found 42 result(s):

    1. annual.pdf (p.5-6)  [cont_mno345]
       ...revenue growth exceeded expectations across all segments...
    2. Q1/summary.docx (p.2)  [cont_xyz789]
       ...growth metrics indicate strong revenue trajectory...

/Reports> search "quarterly earnings" --folder /Reports/Q1 --limit 10

/> search "AI strategy" --folder scope_abc123

/> search "compliance update" --metadata department=Legal --metadata year=2025
```

For full details on search features, see the [Search Guide](search.md).

---

## Shell Control

### help

Show available commands or help for a specific command.

```
/> help

Documented commands (type help <topic>):
========================================
cd  download  exit  help  ls  mkdir  mv  mvdir  pwd  quit  rm  rmdir  search  upload

/> help search
Search files: search <query> [--folder <path|id>] [--metadata key=value ...] [--limit N]
...
```

### exit / quit

Exit the interactive shell. `Ctrl+D` also works.

```
/Reports> exit
```
