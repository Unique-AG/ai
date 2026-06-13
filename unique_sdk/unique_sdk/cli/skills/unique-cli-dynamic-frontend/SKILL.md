---
name: unique-cli-dynamic-frontend
description: >-
  Create, update, and list Unique Dynamic Frontend Spaces using the
  `unique-cli dynamic-frontend` command. Use when deploying a generated
  Dynamic Frontend ZIP, updating an existing Dynamic Frontend Space bundle,
  listing manageable Dynamic Frontend Spaces, or when the user mentions
  Dynamic Frontend Space deployment through the CLI.
---

# Unique CLI -- Dynamic Frontend Spaces

Use `unique-cli dynamic-frontend` to create or update Dynamic Frontend Spaces
from upload-ready ZIP bundles or existing Knowledge Base content IDs.

The CLI is installed via `pip install unique-sdk` and uses the same
`UNIQUE_USER_ID`, `UNIQUE_COMPANY_ID`, `UNIQUE_API_KEY`, `UNIQUE_APP_ID`, and
`UNIQUE_API_BASE` environment variables as the rest of `unique-cli`.

## Create a New Space

To upload a ZIP and create a new Dynamic Frontend Space:

```bash
unique-cli cd /Apps
unique-cli dynamic-frontend deploy \
  --file ./revenue-dashboard.zip \
  --name "Revenue Dashboard"
```

To create from an already uploaded KB content ID:

```bash
unique-cli dynamic-frontend deploy \
  --content-id cont_abc123 \
  --name "Revenue Dashboard"
```

The command prints the created `spaceId`, `contentId`, and direct `URL` when the
API returns it:

```text
Created Dynamic Frontend space "Revenue Dashboard" (space_abc123)
Content: cont_abc123
URL: https://chat.example.com/space/space_abc123
```

## Update an Existing Space

Use `--space-id` to update an existing Dynamic Frontend Space instead of
creating a new one.

Upload a new ZIP and point the existing Space at it:

```bash
unique-cli cd /Apps
unique-cli dynamic-frontend deploy \
  --space-id space_abc123 \
  --file ./revenue-dashboard-1.0.1.zip
```

Update from an already uploaded KB content ID:

```bash
unique-cli dynamic-frontend deploy \
  --space-id space_abc123 \
  --content-id cont_newbundle123
```

Rename while updating the bundle:

```bash
unique-cli dynamic-frontend deploy \
  --space-id space_abc123 \
  --file ./revenue-dashboard-1.0.1.zip \
  --name "Revenue Dashboard"
```

The update command prints the same `spaceId`, `contentId`, and direct `URL`
fields as create.

## List Spaces

List Dynamic Frontend Spaces the current user can manage:

```bash
unique-cli dynamic-frontend list
```

Use JSON output for scripts:

```bash
unique-cli dynamic-frontend list --json
unique-cli dynamic-frontend deploy --space-id space_abc123 --file ./app.zip --json
```

## Rules

- For `--file`, first `unique-cli cd` into the KB folder where the ZIP should be
  uploaded; uploading to root is rejected.
- Use `--space-id` for updates. Without `--space-id`, `deploy` creates a new
  Dynamic Frontend Space and requires `--name`.
- `--file` and `--content-id` are mutually exclusive.
- After create or update, return the CLI output to the user, especially the
  direct `URL`.
