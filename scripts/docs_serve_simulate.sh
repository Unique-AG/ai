#!/usr/bin/env bash
# Simulate production locally: root (mkdocs) on 8000, SDK (mike) on 8001, Toolkit (mike) on 8002.
# Root nav links to http://127.0.0.1:8001/dev/ and http://127.0.0.1:8002/dev/.

set -e
REPO_ROOT="$(git rev-parse --show-toplevel)"
GHPAGES_WORKTREE="${GHPAGES_WORKTREE:-/tmp/ai-gh-pages}"
cd "$REPO_ROOT"

echo "=== 0. Clean slate ==="
rm -rf site unique_sdk/site unique_toolkit/site
git fetch origin gh-pages --depth=1 2>/dev/null || true
poetry run mike delete --all -F unique_sdk/mkdocs.yaml --ignore-remote-status 2>/dev/null || true
poetry run mike delete --all -F unique_toolkit/mkdocs.yaml --ignore-remote-status 2>/dev/null || true

echo ""
echo "=== 1. Build root ==="
poetry run mkdocs build
cp -r site /tmp/root_site
rm -rf site

echo ""
echo "=== 2. Deploy root to gh-pages (worktree) ==="
if git worktree list --porcelain 2>/dev/null | grep -q "worktree $GHPAGES_WORKTREE"; then
  (cd "$GHPAGES_WORKTREE" && git fetch origin gh-pages --depth=1 2>/dev/null; git reset --hard origin/gh-pages 2>/dev/null || true)
elif git show-ref --verify --quiet refs/heads/gh-pages; then
  git worktree add -f "$GHPAGES_WORKTREE" gh-pages
  (cd "$GHPAGES_WORKTREE" && git reset --hard origin/gh-pages 2>/dev/null || true)
else
  git worktree add -f "$GHPAGES_WORKTREE" -b gh-pages
fi
rsync -av --delete --exclude='.git' /tmp/root_site/ "$GHPAGES_WORKTREE/"
(cd "$GHPAGES_WORKTREE" && git add -A && (git diff --staged --quiet || git commit -m "docs: root and tutorials"))
git worktree remove -f "$GHPAGES_WORKTREE" 2>/dev/null || true

echo ""
echo "=== 3. Deploy SDK with mike (site_url=8001 so version selector works) ==="
sed 's|site_url: https://unique-ag.github.io/ai/unique-sdk/|site_url: http://127.0.0.1:8001/|' unique_sdk/mkdocs.yaml > unique_sdk/mkdocs.serve_local.yaml
poetry run mike deploy -F unique_sdk/mkdocs.serve_local.yaml "$(cd unique_sdk && poetry version -s)" dev --update-aliases
rm -f unique_sdk/mkdocs.serve_local.yaml

echo ""
echo "=== 4. Deploy Toolkit with mike (site_url=8002 so version selector works) ==="
sed 's|site_url: https://unique-ag.github.io/ai/unique-toolkit/|site_url: http://127.0.0.1:8002/|' unique_toolkit/mkdocs.yaml > unique_toolkit/mkdocs.serve_local.yaml
poetry run mike deploy -F unique_toolkit/mkdocs.serve_local.yaml "$(cd unique_toolkit && poetry version -s)" dev --update-aliases
rm -f unique_toolkit/mkdocs.serve_local.yaml

echo ""
echo "=== 5. Re-add worktree to serve SDK and Toolkit static files ==="
git worktree add -f "$GHPAGES_WORKTREE" gh-pages

echo ""
echo "=== 6. Serve on three ports (Ctrl+C to stop) ==="
echo "  Root:    http://127.0.0.1:8000  (mkdocs; nav links to 8001 and 8002)"
echo "  SDK:     http://127.0.0.1:8001  (mike versioned; use /dev/ or /latest/)"
echo "  Toolkit: http://127.0.0.1:8002  (mike versioned; use /dev/ or /latest/)"
echo ""

trap 'kill $(jobs -p) 2>/dev/null; git worktree remove -f "$GHPAGES_WORKTREE" 2>/dev/null || true; exit' INT TERM

poetry run mkdocs serve -f mkdocs.serve_local.yaml -a 127.0.0.1:8000 &
(cd "$GHPAGES_WORKTREE/unique-sdk" && python3 -m http.server 8001) &
(cd "$GHPAGES_WORKTREE/unique-toolkit" && python3 -m http.server 8002) &

wait
