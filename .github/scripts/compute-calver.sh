#!/usr/bin/env bash
set -euo pipefail

# Computes the target CalVer cycle (YYYY.WW) for the next release/dev build.
#
# Today's strategy is simple: pick the next even ISO week >= today's ISO
# week, rolling into the following ISO year when week 53 (always odd) or
# a post-52 overflow would otherwise land on an odd week.
#
# Once release-please is wired up and starts maintaining
# `.release-please-manifest.json`, that file will become the source of
# truth for "which cycle did we just ship?" and dev builds will target
# cycle + 2 instead. That manifest-first selector lives in the follow-up
# release-process PR, not here.
#
# Output (stdout): YYYY.WW

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

calver_from_today() {
  local year week
  # TODAY is an optional override used by BATS tests for determinism.
  # In CI and local runs it is unset and we fall back to `date -u`.
  if [[ -n "${TODAY:-}" ]]; then
    year=$(date -u -d "$TODAY" +"%G")
    week=$(date -u -d "$TODAY" +"%V")
  else
    year=$(date -u +"%G")
    week=$(date -u +"%V")
  fi
  # advance_weeks snaps odd results to the next even week, including
  # rolling week 53 (always odd) to week 2 of the next ISO year.
  advance_weeks "$year" "$week" 0
}

# Only execute when invoked directly; sourcing (e.g. from BATS tests)
# gets access to the helper functions without running main.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  calver_from_today
fi
