---
name: unique-cli-dynamic-frontend
description: >-
  Create, update, list, and delete Unique Dynamic Frontend Spaces using the
  `unique-cli dynamic-frontend` command. Use when deploying a generated
  Dynamic Frontend ZIP, updating an existing Dynamic Frontend Space bundle,
  listing manageable Dynamic Frontend Spaces, deleting a deployed Dynamic
  Frontend Space, or when the user mentions Dynamic Frontend Space deployment
  through the CLI.
---

# Unique CLI -- Dynamic Frontend Spaces

Use `unique-cli dynamic-frontend` to create, update, list, and delete Dynamic
Frontend Spaces from upload-ready ZIP bundles or existing Knowledge Base
content IDs.

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

The command prints the created `spaceId`, `contentId`, and **two** URLs when the
API returns them — the user-facing view `URL` (jump into the Space in the chat
app) and the `Config URL` (configure and share the Space in the admin app):

```text
Created Dynamic Frontend space "Revenue Dashboard" (space_abc123)
Content: cont_abc123
URL: https://next.qa.unique.app/chat/space/space_abc123
Config URL: https://next.qa.unique.app/admin/dynamic-frontend-space/space_abc123
```

If the installed SDK/CLI version does not print one of these URLs yet, construct
it from the known frontend base URLs and `spaceId`:

```text
# View URL (chat app)
<chat-frontend-url>/space/<spaceId>
# Config/share URL (admin app)
<admin-frontend-url>/dynamic-frontend-space/<spaceId>
```

On QA, those are:

```text
https://next.qa.unique.app/chat/space/<spaceId>
https://next.qa.unique.app/admin/dynamic-frontend-space/<spaceId>
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

The update command prints the same `spaceId`, `contentId`, view `URL`, and
`Config URL` fields as create.

## Delete a Space

Remove a deployed Dynamic Frontend Space by its space id. This deletes the
backing BYOC app and the owning space (and its access grants):

```bash
unique-cli dynamic-frontend delete space_abc123
```

The command prints a confirmation:

```text
Deleted Dynamic Frontend space space_abc123
```

Deletion is permanent and requires manage access on the space (or a
company-wide space-admin role). Always confirm the correct `spaceId` with the
user before deleting — there is no undo.

## List Spaces

List Dynamic Frontend Spaces the current user can manage:

```bash
unique-cli dynamic-frontend list
```

Use JSON output for scripts:

```bash
unique-cli dynamic-frontend list --json
unique-cli dynamic-frontend deploy --space-id space_abc123 --file ./app.zip --json
unique-cli dynamic-frontend delete space_abc123 --json
```

## Rules

- For `--file`, first `unique-cli cd` into the KB folder where the ZIP should be
  uploaded; uploading to root is rejected.
- Use `--space-id` for updates. Without `--space-id`, `deploy` creates a new
  Dynamic Frontend Space and requires `--name`.
- `--file` and `--content-id` are mutually exclusive.
- `delete` is permanent and has no undo — confirm the `spaceId` with the user
  first, and never guess which space to delete.
- After create or update, return the CLI output to the user, especially both the
  view `URL` (jump to the Space) and the `Config URL` (configure/share the Space).
- Never report the BYOC iframe runtime URL
  (`https://byoc.../serve/df-assistant-...`) as the Space URL; it is an
  internal iframe launch URL, not the navigation link users need.
