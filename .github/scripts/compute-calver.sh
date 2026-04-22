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

# Number of ISO weeks in a given ISO year (52 or 53).
#
# ISO 8601 long years have 53 weeks; this happens roughly once every 5–6
# years (e.g. 2020, 2026, 2032). Dec 28 always falls in the last ISO week
# of its ISO year, so its week number is the total count. Requires GNU
# date, which is fine on the Linux runners that execute this script.
iso_weeks_in_year() {
  local y="$1"
  local w
  w=$(date -u -d "${y}-12-28" +"%V")
  echo $((10#$w))
}

# Advance (year, week) by `step` ISO weeks, rolling into the next ISO year
# once we exceed that year's week count (52 or 53). The output is always
# an even ISO week — releases only ship on even weeks, and week 53 (when
# it exists) is always odd, so a naive "+2" from week 52 of a 53-week year
# (giving week 54) must land on week 2 of the next year, not week 1.
advance_weeks() {
  local year="$1" week="$2" step="$3"
  week=$((10#$week + step))
  local total
  while :; do
    total=$(iso_weeks_in_year "$year")
    if (( week > total )); then
      week=$((week - total))
      year=$((year + 1))
      continue
    fi
    if (( week % 2 != 0 )); then
      week=$((week + 1))
      continue
    fi
    break
  done
  printf "%04d.%02d\n" "$year" "$week"
}

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
  advance_weeks "$y" "$w" 2
}

calver_from_today() {
  local year week
  year=$(date -u +"%G")
  week=$(date -u +"%V")
  # advance_weeks snaps odd results to the next even week, including
  # rolling week 53 (always odd) to week 2 of the next ISO year.
  advance_weeks "$year" "$week" 0
}

if out=$(calver_from_manifest); then
  echo "$out"
else
  calver_from_today
fi
