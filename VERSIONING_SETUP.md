# Documentation Versioning Setup

This document describes the documentation setup: **root site with full nav** (including links to versioned SDK and Toolkit) and **separate mike versioning** for Unique SDK and Unique Toolkit.

## Overview

- **Root site** (at `/`): Built from the repo root. Contains Home, Implementation Guidelines, **nav links** to Unique SDK and Unique Toolkit (which open the versioned sub-sites), and **Tutorials** (included via monorepo).
- **Unique SDK** (at `/unique-sdk/`): Versioned with mike. Own version dropdown; versions like `dev`, `latest`, `0.10.75`.
- **Unique Toolkit** (at `/unique-toolkit/`): Versioned with mike. Own version dropdown; versions like `dev`, `latest`, `1.45.9`.

So you keep one navbar on the root that links out to the versioned SDK and Toolkit docs.

## Architecture

```
https://unique-ag.github.io/ai/
├── index.html                    # Root landing (Home, Guidelines, Tutorials)
├── Implementation Guidelines/
├── Tutorials/                    # From monorepo !include
├── unique-sdk/
│   ├── 0.10.75/
│   ├── dev/
│   ├── latest/
│   └── versions.json
└── unique-toolkit/
    ├── 1.45.9/
    ├── dev/
    ├── latest/
    └── versions.json
```

Root nav entries "Unique SDK" and "Unique Toolkit" are **links** to `.../unique-sdk/latest/` and `.../unique-toolkit/latest/`.

## Where `gh-pages` is used

The **`gh-pages`** branch is the only place the built documentation lives. Everything in the doc flow writes to or reads from it:

| What | How it uses gh-pages |
|------|----------------------|
| **CI workflow** | Builds root → copies to gh-pages root → pushes. Then `mike deploy` adds SDK and Toolkit under `unique-sdk/` and `unique-toolkit/` on the same branch and pushes. |
| **GitHub Pages (live site)** | Repo **Settings → Pages → Build and deployment → Source**: must be **"Deploy from a branch"** with branch **`gh-pages`**. GitHub then serves the contents of that branch at `https://unique-ag.github.io/ai/`. If Source is "GitHub Actions" or another branch, the live site will not use this setup. |
| **Local `mike serve`** | Serves the **local** gh-pages branch (e.g. `http://127.0.0.1:8000/`). So whatever you deployed to gh-pages locally is what you see. |

So: **gh-pages = the built static site**. There is no separate “publish” step; pushing to gh-pages (or having CI push to it) is the publish. For the live site to match, GitHub Pages must be set to deploy from the **gh-pages** branch.

## Configuration

### Root `mkdocs.yaml`

- **nav**: Home, Implementation Guidelines, **Unique SDK** → `https://unique-ag.github.io/ai/unique-sdk/latest/`, **Unique Toolkit** → `https://unique-ag.github.io/ai/unique-toolkit/latest/`, **Tutorials** → `!include ./tutorials/mkdocs.yaml`.
- **plugins**: `monorepo` (only for Tutorials).
- No `extra.version` (root has no version selector).

### `unique_sdk/mkdocs.yaml`

- **site_url**: `https://unique-ag.github.io/ai/unique-sdk/`
- **extra.version.provider**: `mike`
- **plugins**: include **mike** with **deploy_prefix: unique-sdk** so mike deploys under `/unique-sdk/`.

### `unique_toolkit/mkdocs.yaml`

- **site_url**: `https://unique-ag.github.io/ai/unique-toolkit/`
- **extra.version.provider**: `mike`
- **plugins**: include **mike** with **deploy_prefix: unique-toolkit**.

## Workflow (`.github/workflows/docs_deploy.yaml`)

1. **Build root** from repo root (`mkdocs build`).
2. **Deploy root to gh-pages**: Checkout `gh-pages`, copy root build to branch root (keeps existing `unique-sdk/` and `unique-toolkit/`), push.
3. **Mike deploy SDK**: `mike deploy -F unique_sdk/mkdocs.yaml ...` so SDK docs go to `unique-sdk/` (via `deploy_prefix` in that config).
4. **Mike deploy Toolkit**: Same with `unique_toolkit/mkdocs.yaml` and `unique-toolkit/`.

**Triggers**: Push to `main` (path filters for docs/mkdocs), or tags `sdk-v*`, `toolkit-v*`.

- **main**: Root + SDK (dev) + Toolkit (dev).
- **Tag `sdk-v0.10.76`**: SDK release (deploy that version as `latest`).
- **Tag `toolkit-v1.45.10`**: Toolkit release (deploy that version as `latest`).

## Local testing

Run all commands from the **repo root** unless stated otherwise. Use the root Poetry env (mike is installed there).

---

### 0. Clean slate (clear old versions and cache)

Use this when you want to reset local docs and re-run everything (e.g. to get rid of old 0.1.0 / 1.45 deploys).

```bash
# From repo root
cd /path/to/ai

# 1. Remove build output
rm -rf site unique_sdk/site unique_toolkit/site

# 2. Fetch gh-pages so mike has something to work on
git fetch origin gh-pages --depth=1 2>/dev/null || true

# 3. Remove all versioned SDK docs from gh-pages (local branch only; no --push)
poetry run mike delete --all -F unique_sdk/mkdocs.yaml --ignore-remote-status

# 4. Remove all versioned Toolkit docs from gh-pages (local only)
poetry run mike delete --all -F unique_toolkit/mkdocs.yaml --ignore-remote-status
```

Then run **“Full local run”** below.

---

### 1. Prerequisites

```bash
# Install dependencies (includes mike)
poetry install --with dev

# Ensure gh-pages exists locally (mike needs it to deploy/serve)
git fetch origin gh-pages 2>/dev/null || true
```

If `gh-pages` does not exist yet, the first `mike deploy` below will create it.

---

### 1a. Simulate production locally (root mkdocs, SDK/Toolkit mike, nav links)

To simulate the real setup on three ports – root with nav linking to versioned SDK and Toolkit:

```bash
./scripts/docs_serve_simulate.sh
```

This will:

1. Clean, build root, deploy root to gh-pages (worktree), then **mike deploy** SDK and Toolkit so they have versioning.
2. Serve **root** with **mkdocs** on **8000** using `mkdocs.serve_local.yaml` (nav points to 8001 and 8002).
3. Serve **SDK** (mike-built, versioned) on **8001** and **Toolkit** on **8002** via a static server from the gh-pages worktree.

| Port | Site     | URL                       |
|------|----------|---------------------------|
| 8000 | Root     | http://127.0.0.1:8000     |
| 8001 | SDK      | http://127.0.0.1:8001/dev/ (version dropdown) |
| 8002 | Toolkit  | http://127.0.0.1:8002/dev/ (version dropdown) |

Root’s nav entries “Unique SDK” and “Unique Toolkit” open 8001 and 8002. Press Ctrl+C to stop all; the worktree is removed on exit.

---

### 1a-alt. Serve on three ports (no versioning)

If you only want to edit and preview without gh-pages or mike:

```bash
./scripts/docs_serve_three_ports.sh
```

Root, SDK, and Toolkit each run with `mkdocs serve` on 8000, 8001, 8002. No version dropdowns.

---

### 1b. Full local run (root + SDK + Toolkit)

One sequence to build, deploy locally (no push), and serve. Do **Clean slate (0)** first if you want to clear old versions.

**Or run the script** (does clean slate + full run + serve). The script uses a **git worktree** for gh-pages so it **never checks out gh-pages in your repo** – you stay on your current branch (with all your mike config and doc changes) the whole time:

```bash
./scripts/docs_serve_local.sh
```

You can set `GHPAGES_WORKTREE` to use a different path (default is `/tmp/ai-gh-pages`).

```bash
# From repo root
cd "$(git rev-parse --show-toplevel)"

# 1) Build root site
poetry run mkdocs build
cp -r site /tmp/root_site

# 2) Update gh-pages with root content (local only). Stash first so checkout doesn't overwrite uncommitted changes.
git stash push -m "temp" --include-untracked 2>/dev/null || true
git fetch origin gh-pages --depth=1 2>/dev/null || true
git checkout gh-pages 2>/dev/null || git checkout --orphan gh-pages
git reset --hard origin/gh-pages 2>/dev/null || true
rsync -av /tmp/root_site/ .
git add -A
git diff --staged --quiet || git commit -m "docs: root and tutorials"
git checkout -
git stash pop 2>/dev/null || true
rm -rf site

# 3) Deploy SDK (version from unique_sdk/pyproject.toml) as dev
poetry run mike deploy -F unique_sdk/mkdocs.yaml $(cd unique_sdk && poetry version -s) dev --update-aliases

# 4) Deploy Toolkit (version from unique_toolkit/pyproject.toml) as dev
poetry run mike deploy -F unique_toolkit/mkdocs.yaml $(cd unique_toolkit && poetry version -s) dev --update-aliases

# 5) Serve (all three: root, SDK, Toolkit)
poetry run mike serve -F unique_sdk/mkdocs.yaml
```

Then open:

| Page | URL |
|------|-----|
| Root | http://127.0.0.1:8000/ |
| SDK (version dropdown) | http://127.0.0.1:8000/unique-sdk/dev/ |
| Toolkit (version dropdown) | http://127.0.0.1:8000/unique-toolkit/dev/ |

Versions come from `unique_sdk/pyproject.toml` and `unique_toolkit/pyproject.toml` (e.g. 0.10.75 and 1.45.9).

---

### 2. Test the root site only (no versioning)

Build and serve the root docs (Home, Guidelines, Tutorials). Nav links “Unique SDK” and “Unique Toolkit” will point at production; they will 404 if you haven’t deployed yet.

```bash
poetry run mkdocs build
poetry run mkdocs serve
```

Open **http://127.0.0.1:8000**. Check Home, Implementation Guidelines, and Tutorials.

---

### 3. Test SDK with mike (version dropdown)

Deploy the current SDK version into the local `gh-pages` layout, then serve it so you see the version selector.

```bash
# Deploy current SDK version as "dev" (writes under unique-sdk/ in gh-pages)
poetry run mike deploy -F unique_sdk/mkdocs.yaml $(cd unique_sdk && poetry version -s) dev --update-aliases

# Serve the versioned site (reads from gh-pages)
poetry run mike serve -F unique_sdk/mkdocs.yaml
```

Open **http://127.0.0.1:8000/unique-sdk/dev/** (or the URL printed by `mike serve`). You should see the SDK docs and the version dropdown.

---

### 4. Test Toolkit with mike (version dropdown)

Same idea for the toolkit:

```bash
poetry run mike deploy -F unique_toolkit/mkdocs.yaml $(cd unique_toolkit && poetry version -s) dev --update-aliases
poetry run mike serve -F unique_toolkit/mkdocs.yaml
```

Open **http://127.0.0.1:8000/unique-toolkit/dev/**.

---

### 5. Test the full flow (root + SDK + Toolkit) like CI

This mirrors what the workflow does: root at `/`, SDK at `/unique-sdk/`, Toolkit at `/unique-toolkit/`. Do it in this order.

**Step A – Deploy root to gh-pages**

Either use the script (recommended; it uses a worktree so you never leave your branch), or manually with a worktree so you stay on your branch:

```bash
poetry run mkdocs build
cp -r site /tmp/root_site
rm -rf site
git fetch origin gh-pages --depth=1 2>/dev/null || true
# Use a worktree so we don't checkout gh-pages in the main repo
git worktree add -f /tmp/ai-gh-pages gh-pages 2>/dev/null || git worktree add -f /tmp/ai-gh-pages -b gh-pages
(cd /tmp/ai-gh-pages && git reset --hard origin/gh-pages 2>/dev/null || true)
rsync -av --delete /tmp/root_site/ /tmp/ai-gh-pages/
(cd /tmp/ai-gh-pages && git add -A && (git diff --staged --quiet || git commit -m "docs: root and tutorials"))
git worktree remove -f /tmp/ai-gh-pages 2>/dev/null || true
```

**Step B – Deploy SDK and Toolkit with mike (no push)**

```bash
# SDK
poetry run mike deploy -F unique_sdk/mkdocs.yaml $(cd unique_sdk && poetry version -s) dev --update-aliases

# Toolkit
poetry run mike deploy -F unique_toolkit/mkdocs.yaml $(cd unique_toolkit && poetry version -s) dev --update-aliases
```

**Step C – Serve and open**

```bash
poetry run mike serve -F unique_sdk/mkdocs.yaml
```

Then open:

- **http://127.0.0.1:8000/** – root (Home, Guidelines, Tutorials)
- **http://127.0.0.1:8000/unique-sdk/dev/** – SDK (with version dropdown)
- **http://127.0.0.1:8000/unique-toolkit/dev/** – Toolkit (with version dropdown)

From the root page, the nav links “Unique SDK” and “Unique Toolkit” point to production URLs. To test those links locally, temporarily change the root `mkdocs.yaml` nav to use relative URLs: `unique-sdk/dev/` and `unique-toolkit/dev/`, then rebuild the root and repeat Step A and C.

---

### 6. Useful mike commands (from repo root)

```bash
# List deployed versions for a sub-project
poetry run mike list -F unique_sdk/mkdocs.yaml
poetry run mike list -F unique_toolkit/mkdocs.yaml

# Delete a version (e.g. to re-deploy)
poetry run mike delete -F unique_sdk/mkdocs.yaml 0.10.75

# Deploy a second version (e.g. "latest") for the same project
poetry run mike deploy -F unique_sdk/mkdocs.yaml 0.10.75 latest --update-aliases
```

## GitHub Pages

- In the repo: **Settings → Pages**.
- Under **Build and deployment**, set **Source** to **"Deploy from a branch"**.
- Choose branch **`gh-pages`** and root **/ (root)**. Save.
- The live site at `https://unique-ag.github.io/ai/` will then serve whatever is on the `gh-pages` branch (same as what CI and mike push to).

## Version aliases (per sub-site)

- **dev**: Latest deploy from `main`.
- **latest**: Latest release (from `sdk-v*` or `toolkit-v*` tag).
- **x.y.z**: Specific version from a tag.

## Cross-links

- From root or any page: use full URLs, e.g. `https://unique-ag.github.io/ai/unique-sdk/latest/`, `https://unique-ag.github.io/ai/unique-toolkit/latest/`.
- From within SDK or Toolkit docs: use relative paths under their base (e.g. `../` for root) or full URLs to the other sub-site.
