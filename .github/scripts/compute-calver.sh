#!/usr/bin/env bash
set -euo pipefail

# Computes the target CalVer cycle (YYYY.WW) for the next release/dev build.
#
# Strategy:
#   1. If .release-please-manifest.json contains at least one CalVer value
#      (YYYY.WW.N), take the highest and advance by one release cycle
#      (+2 ISO weeks). This covers the normal steady state — after release X
#      is cut, dev builds target X+2.
#   2. Otherwise (bootstrap, no CalVer in manifest yet), pick the next
#      even ISO week >= today's ISO week.
#
# Output (stdout): YYYY.WW

MANIFEST="${MANIFEST:-.release-please-manifest.json}"

calver_from_manifest() {
  [[ -f "$MANIFEST" ]] || return 1
  local highest
  highest=$(jq -r '.. | strings | select(test("^[0-9]{4}\\.[0-9]{2}\\.[0-9]+$"))' "$MANIFEST" \
            | sort -V | tail -n 1)
  [[ -n "$highest" ]] || return 1
  local y w
  y="${highest%%.*}"
  w="${highest#*.}"
  w="${w%%.*}"
  local week=$((10#$w + 2))
  local year=$((10#$y))
  if (( week > 52 )); then
    week=$((week - 52))
    year=$((year + 1))
  fi
  printf "%04d.%02d\n" "$year" "$week"
}

calver_from_today() {
  local year week
  year=$(date -u +"%G")
  week=$(date -u +"%V")
  week=$((10#$week))
  if (( week % 2 != 0 )); then
    week=$((week + 1))
  fi
  if (( week > 52 )); then
    week=$((week - 52))
    year=$((year + 1))
  fi
  printf "%04d.%02d\n" "$year" "$week"
}

if out=$(calver_from_manifest); then
  echo "$out"
else
  calver_from_today
fi
