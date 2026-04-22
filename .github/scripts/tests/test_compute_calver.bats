#!/usr/bin/env bats
#
# Tests for .github/scripts/compute-calver.sh
#
# compute-calver.sh encodes two bits of subtle logic that are worth
# pinning down with regression tests:
#
#   1. ISO 8601 "long years" — years whose ISO calendar has 53 weeks
#      instead of 52 (e.g. 2020, 2026, 2032). Naively adding 2 weeks
#      from week 52 of such a year lands on week 54, which must roll
#      into week 2 of the next ISO year, not week 1.
#
#   2. Even-week enforcement — releases only ship on even ISO weeks.
#      Any derived odd week (including the always-odd week 53) must
#      be snapped forward to the next even week, chaining into the
#      year rollover above when needed.
#
# The script today has a single mode:
#   - `calver_from_today`: start from today's ISO (year, week) and
#     snap to the next even week (+0 through advance_weeks).
#
# The manifest-first selector (pick the highest CalVer in
# .release-please-manifest.json and advance by +2) ships in the
# follow-up release-process PR alongside release-please itself, so
# its tests live there too.

load test_helper

SCRIPT="$SCRIPTS_DIR/compute-calver.sh"

setup() {
    export TEST_TMPDIR="$(mktemp -d)"
    cd "$TEST_TMPDIR" || exit 1

    # compute-calver.sh relies on GNU `date -u -d "..."` syntax, which is
    # what the Linux GitHub Actions runners provide. On macOS the system
    # `date` is BSD and rejects `-d`, which would cause iso_weeks_in_year
    # to return 0 and advance_weeks to spin forever. When a GNU `gdate`
    # is available (`brew install coreutils`), shim it as `date` for the
    # duration of the test so the same suite runs green locally too.
    if [[ "$OSTYPE" == darwin* ]] && command -v gdate >/dev/null 2>&1; then
        export GDATE_SHIM_DIR="$TEST_TMPDIR/shim"
        mkdir -p "$GDATE_SHIM_DIR"
        ln -sf "$(command -v gdate)" "$GDATE_SHIM_DIR/date"
        export PATH="$GDATE_SHIM_DIR:$PATH"
    fi

    # shellcheck source=/dev/null
    source "$SCRIPT"
}

teardown() {
    cd "$TESTS_DIR" || true
    if [ -n "$TEST_TMPDIR" ] && [ -d "$TEST_TMPDIR" ]; then
        rm -rf "$TEST_TMPDIR"
    fi
}

# ---------------------------------------------------------------------------
# iso_weeks_in_year
# ---------------------------------------------------------------------------

@test "iso_weeks_in_year: 2024 has 52 weeks" {
    run iso_weeks_in_year 2024
    [ "$status" -eq 0 ]
    [ "$output" = "52" ]
}

@test "iso_weeks_in_year: 2025 has 52 weeks" {
    run iso_weeks_in_year 2025
    [ "$status" -eq 0 ]
    [ "$output" = "52" ]
}

@test "iso_weeks_in_year: 2026 is an ISO long year with 53 weeks" {
    run iso_weeks_in_year 2026
    [ "$status" -eq 0 ]
    [ "$output" = "53" ]
}

@test "iso_weeks_in_year: 2020 is an ISO long year with 53 weeks" {
    run iso_weeks_in_year 2020
    [ "$status" -eq 0 ]
    [ "$output" = "53" ]
}

@test "iso_weeks_in_year: 2027 has 52 weeks" {
    run iso_weeks_in_year 2027
    [ "$status" -eq 0 ]
    [ "$output" = "52" ]
}

# ---------------------------------------------------------------------------
# advance_weeks
# ---------------------------------------------------------------------------

@test "advance_weeks: +2 within the same year on an even starting week" {
    run advance_weeks 2025 10 2
    [ "$status" -eq 0 ]
    [ "$output" = "2025.12" ]
}

@test "advance_weeks: +0 snaps an odd starting week to the next even week" {
    run advance_weeks 2025 11 0
    [ "$status" -eq 0 ]
    [ "$output" = "2025.12" ]
}

@test "advance_weeks: +0 is a no-op on an already-even week" {
    run advance_weeks 2025 12 0
    [ "$status" -eq 0 ]
    [ "$output" = "2025.12" ]
}

@test "advance_weeks: +2 from odd week snaps forward even across the add" {
    # 11 + 2 = 13 (odd) -> snap to 14
    run advance_weeks 2025 11 2
    [ "$status" -eq 0 ]
    [ "$output" = "2025.14" ]
}

@test "advance_weeks: +2 rolls into next year from week 52 of a 52-week year" {
    # 2025 has 52 ISO weeks. 52 + 2 = 54 > 52 -> year++, week=2 (even).
    run advance_weeks 2025 52 2
    [ "$status" -eq 0 ]
    [ "$output" = "2026.02" ]
}

@test "advance_weeks: +2 rolls into next year from week 52 of a 53-week year" {
    # 2026 has 53 ISO weeks. 52 + 2 = 54 > 53 -> year++, week=1, odd, snap=2.
    run advance_weeks 2026 52 2
    [ "$status" -eq 0 ]
    [ "$output" = "2027.02" ]
}

@test "advance_weeks: the always-odd week 53 snaps into week 2 of next year" {
    # Starting on ISO week 53 (only possible in long years). +0 must still
    # snap because 53 is odd, which rolls into week 2 of 2027.
    run advance_weeks 2026 53 0
    [ "$status" -eq 0 ]
    [ "$output" = "2027.02" ]
}

@test "advance_weeks: +2 from week 51 of a 53-week year chains through week 53" {
    # 51 + 2 = 53 (odd, and the last week of 2026) -> snap to 54 -> wrap
    # to week 1 of 2027 -> odd, snap to week 2. Final: 2027.02.
    run advance_weeks 2026 51 2
    [ "$status" -eq 0 ]
    [ "$output" = "2027.02" ]
}

@test "advance_weeks: pads single-digit weeks to two digits in the output" {
    run advance_weeks 2025 2 0
    [ "$status" -eq 0 ]
    [ "$output" = "2025.02" ]
}

# ---------------------------------------------------------------------------
# calver_from_today (deterministic via TODAY)
# ---------------------------------------------------------------------------

@test "calver_from_today: already-even ISO week is returned as-is" {
    # 2025-03-05 is ISO week 10 of 2025 (Wednesday).
    TODAY=2025-03-05 run calver_from_today
    [ "$status" -eq 0 ]
    [ "$output" = "2025.10" ]
}

@test "calver_from_today: odd ISO week snaps forward to the next even week" {
    # 2025-03-12 is ISO week 11 of 2025 -> snap to 12.
    TODAY=2025-03-12 run calver_from_today
    [ "$status" -eq 0 ]
    [ "$output" = "2025.12" ]
}

@test "calver_from_today: ISO week 53 of 2026 rolls into 2027.02" {
    # 2026-12-28 falls in ISO week 53 of 2026 (always odd, only exists in
    # long years). The +0 path must snap through the year boundary.
    TODAY=2026-12-28 run calver_from_today
    [ "$status" -eq 0 ]
    [ "$output" = "2027.02" ]
}

# ---------------------------------------------------------------------------
# script as a whole (invoked, not sourced)
# ---------------------------------------------------------------------------

@test "compute-calver.sh: emits today's cycle when invoked directly" {
    # 2025-03-05 -> ISO week 10 of 2025, already even.
    TODAY=2025-03-05 run bash "$SCRIPT"
    [ "$status" -eq 0 ]
    [ "$output" = "2025.10" ]
}
