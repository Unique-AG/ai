#!/usr/bin/env bash
# Run from repo root: ./scripts/docs_serve_local.sh
# Cleans old versioned docs, builds root + SDK + Toolkit, serves locally (no push).
# Uses a git worktree for gh-pages so we never leave your current branch.

set -e
REPO_ROOT="$(git rev-parse --show-toplevel)"
GHPAGES_WORKTREE="${GHPAGES_WORKTREE:-/tmp/ai-gh-pages}"
cd "$REPO_ROOT"

echo "=== 0. Clean slate (remove old versions and build output) ==="
rm -rf site unique_sdk/site unique_toolkit/site
git fetch origin gh-pages --depth=1 2>/dev/null || true
poetry run mike delete --all -F unique_sdk/mkdocs.yaml --ignore-remote-status 2>/dev/null || true
poetry run mike delete --all -F unique_toolkit/mkdocs.yaml --ignore-remote-status 2>/dev/null || true

echo ""
echo "=== 1. Build root site ==="
poetry run mkdocs build
cp -r site /tmp/root_site
rm -rf site

echo ""
echo "=== 2. Deploy root to gh-pages via worktree (you stay on your current branch) ==="
if git worktree list --porcelain 2>/dev/null | grep -q "worktree $GHPAGES_WORKTREE"; then
  (cd "$GHPAGES_WORKTREE" && git fetch origin gh-pages --depth=1 2>/dev/null; git reset --hard origin/gh-pages 2>/dev/null || true)
elif git show-ref --verify --quiet refs/heads/gh-pages; then
  git worktree add -f "$GHPAGES_WORKTREE" gh-pages
  (cd "$GHPAGES_WORKTREE" && git reset --hard origin/gh-pages 2>/dev/null || true)
else
  git worktree add -f "$GHPAGES_WORKTREE" -b gh-pages
fi
# Keep .git so the worktree stays a valid repo (--delete would remove it otherwise)
rsync -av --delete --exclude='.git' /tmp/root_site/ "$GHPAGES_WORKTREE/"
(cd "$GHPAGES_WORKTREE" && git add -A && (git diff --staged --quiet || git commit -m "docs: root and tutorials"))
git worktree remove -f "$GHPAGES_WORKTREE" 2>/dev/null || true

echo ""
echo "=== 3. Deploy SDK (version: $(cd unique_sdk && poetry version -s)) as dev ==="
poetry run mike deploy -F unique_sdk/mkdocs.yaml "$(cd unique_sdk && poetry version -s)" dev --update-aliases

echo ""
echo "=== 4. Deploy Toolkit (version: $(cd unique_toolkit && poetry version -s)) as dev ==="
poetry run mike deploy -F unique_toolkit/mkdocs.yaml "$(cd unique_toolkit && poetry version -s)" dev --update-aliases

echo ""
echo "=== 5. Serve (Ctrl+C to stop) ==="
echo "  Root:    http://127.0.0.1:8000/"
echo "  SDK:     http://127.0.0.1:8000/unique-sdk/dev/"
echo "  Toolkit: http://127.0.0.1:8000/unique-toolkit/dev/"
echo ""
poetry run mike serve -F unique_sdk/mkdocs.yaml
