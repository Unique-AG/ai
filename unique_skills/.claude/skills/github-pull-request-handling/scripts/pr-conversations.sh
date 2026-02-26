#!/usr/bin/env bash
# List PR review threads (conversations) in a readable CLI format.
# Usage: pr-conversations.sh [--all] [PR_NUMBER]
#   --all    Show all threads (default: only unresolved)
# Requires: gh, jq

set -euo pipefail

# ANSI colors (disabled when piped)
if [ -t 1 ]; then
  BOLD='\033[1m'    DIM='\033[2m'
  RED='\033[31m'    GREEN='\033[32m'  YELLOW='\033[33m'
  BLUE='\033[34m'   MAGENTA='\033[35m' CYAN='\033[36m'
  WHITE='\033[97m'  RESET='\033[0m'
else
  BOLD='' DIM='' RED='' GREEN='' YELLOW='' BLUE='' MAGENTA='' CYAN='' WHITE='' RESET=''
fi

SHOW_ALL=false
PR=""

for arg in "$@"; do
  case "$arg" in
    --all) SHOW_ALL=true ;;
    *)     PR="$arg" ;;
  esac
done

OWNER_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
OWNER="${OWNER_REPO%%/*}"
REPO="${OWNER_REPO##*/}"
PR=${PR:-$(gh pr view --json number -q .number)}

FILTER='if $show_all then . else map(select(.isResolved | not)) end'

QUERY='
query($owner: String!, $repo: String!, $pr: Int!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          isResolved
          isOutdated
          path
          line
          originalLine
          comments(first: 50) {
            nodes {
              databaseId
              author { login }
              body
              createdAt
            }
          }
        }
      }
    }
  }
}'

THREADS="[]"
CURSOR=""

while true; do
  CURSOR_ARGS=()
  if [ -n "$CURSOR" ]; then
    CURSOR_ARGS=(-F cursor="$CURSOR")
  fi

  PAGE=$(gh api graphql \
    -F owner="$OWNER" \
    -F repo="$REPO" \
    -F pr="$PR" \
    "${CURSOR_ARGS[@]}" \
    -f query="$QUERY")

  THREADS=$(echo "$THREADS" "$PAGE" | jq -s '
    .[0] + (.[1].data.repository.pullRequest.reviewThreads.nodes)')

  HAS_NEXT=$(echo "$PAGE" | jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.hasNextPage')
  if [ "$HAS_NEXT" != "true" ]; then break; fi
  CURSOR=$(echo "$PAGE" | jq -r '.data.repository.pullRequest.reviewThreads.pageInfo.endCursor')
done

TOTAL=$(echo "$THREADS" | jq 'length')
UNRESOLVED=$(echo "$THREADS" | jq '[.[] | select(.isResolved | not)] | length')

if [ "$SHOW_ALL" = true ]; then
  printf "${BOLD}PR #${PR}${RESET} — ${TOTAL} threads, ${YELLOW}${UNRESOLVED} unresolved${RESET} ${DIM}(${OWNER_REPO})${RESET}\n"
else
  printf "${BOLD}PR #${PR}${RESET} — ${YELLOW}${UNRESOLVED} unresolved${RESET} of ${TOTAL} ${DIM}(${OWNER_REPO})${RESET}\n"
fi
echo ""

echo "$THREADS" | jq -r --argjson show_all "$SHOW_ALL" '
  '"$FILTER"' |
  sort_by(.path, (.line // .originalLine // 0))[] |

  (.path + (if (.line // .originalLine) != null
    then ":" + ((.line // .originalLine) | tostring) else "" end)) as $loc |

  (if .isResolved then "resolved"
   elif .isOutdated then "outdated"
   else "open" end) as $state |

  ("__THREAD__" + $state + "__" + $loc +
    (if .isOutdated and (.isResolved | not) then "  (outdated)" else "" end)),

  (.comments.nodes | to_entries[] |
    "__COMMENT__" +
    (if .key == 0 then "root" else "reply" end) + "__" +
    (.value.databaseId | tostring) + "__" +
    (.value.author.login) + "__" +
    ((.value.body // "") | split("\n")[0:2] | join(" ") | gsub("  +"; " ") |
      if length > 80 then .[0:80] + "…" else . end)
  ),
  "__BLANK__"
' | while IFS= read -r line; do
  case "$line" in
    __THREAD__resolved__*)
      loc="${line#__THREAD__resolved__}"
      printf "\n${GREEN}✓${RESET} ${DIM}▸ ${loc}${RESET}\n"
      ;;
    __THREAD__outdated__*)
      loc="${line#__THREAD__outdated__}"
      printf "\n${YELLOW}⚠${RESET} ${CYAN}▸ ${loc}${RESET}\n"
      ;;
    __THREAD__open__*)
      loc="${line#__THREAD__open__}"
      printf "\n${RED}○${RESET} ${BOLD}${CYAN}▸ ${loc}${RESET}\n"
      ;;
    __COMMENT__root__*)
      rest="${line#__COMMENT__root__}"
      id="${rest%%__*}"; rest="${rest#*__}"
      author="${rest%%__*}"; rest="${rest#*__}"
      body="$rest"
      printf "  ${BOLD}●${RESET} ${DIM}%s${RESET}  ${MAGENTA}@%s${RESET}\n" "$id" "$author"
      printf "    ${WHITE}%s${RESET}\n" "$body"
      ;;
    __COMMENT__reply__*)
      rest="${line#__COMMENT__reply__}"
      id="${rest%%__*}"; rest="${rest#*__}"
      author="${rest%%__*}"; rest="${rest#*__}"
      body="$rest"
      printf "  ${DIM}└${RESET} ${DIM}%s${RESET}  ${BLUE}@%s${RESET}\n" "$id" "$author"
      printf "    ${WHITE}%s${RESET}\n" "$body"
      ;;
    __BLANK__)
      ;;
  esac
done

echo ""
printf "${DIM}Reply template:${RESET}\n"
printf "  ${DIM}gh api repos/${OWNER_REPO}/pulls/${PR}/comments -X POST --input - <<'JSON'${RESET}\n"
printf "  ${DIM}{ \"body\": \"Fixed in [HASH](https://github.com/${OWNER_REPO}/commit/HASH)\", \"in_reply_to\": COMMENT_ID }${RESET}\n"
printf "  ${DIM}JSON${RESET}\n"
