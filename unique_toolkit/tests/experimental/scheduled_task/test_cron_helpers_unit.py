"""Unit tests for the :class:`Cron` convenience catalogue."""

from __future__ import annotations

import pytest

from unique_toolkit.experimental.scheduled_task import Cron


def test_AI_cron_enum_members_are_str_subclasses() -> None:
    """Cron members are real strings, so they can be passed anywhere a cron string is expected."""
    assert isinstance(Cron.DAILY_MIDNIGHT, str)
    assert Cron.DAILY_MIDNIGHT == "0 0 * * *"


@pytest.mark.parametrize(
    ("member", "expected"),
    [
        (Cron.EVERY_MINUTE, "* * * * *"),
        (Cron.EVERY_FIVE_MINUTES, "*/5 * * * *"),
        (Cron.EVERY_FIFTEEN_MINUTES, "*/15 * * * *"),
        (Cron.EVERY_THIRTY_MINUTES, "*/30 * * * *"),
        (Cron.HOURLY, "0 * * * *"),
        (Cron.DAILY_MIDNIGHT, "0 0 * * *"),
        (Cron.DAILY_NOON, "0 12 * * *"),
        (Cron.DAILY_9AM, "0 9 * * *"),
        (Cron.WEEKDAYS_9AM, "0 9 * * 1-5"),
        (Cron.WEEKDAYS_MIDNIGHT, "0 0 * * 1-5"),
        (Cron.WEEKENDS_MIDNIGHT, "0 0 * * 0,6"),
        (Cron.WEEKLY_SUNDAY_MIDNIGHT, "0 0 * * 0"),
        (Cron.WEEKLY_MONDAY_MIDNIGHT, "0 0 * * 1"),
        (Cron.MONTHLY_FIRST_MIDNIGHT, "0 0 1 * *"),
        (Cron.MONTHLY_FIFTEENTH_MIDNIGHT, "0 0 15 * *"),
        (Cron.YEARLY_JAN_FIRST, "0 0 1 1 *"),
    ],
)
def test_AI_cron_enum_values_match_expected_wire_strings(
    member: Cron, expected: str
) -> None:
    """Every Cron enum member renders to its canonical 5-field cron string."""
    assert str(member) == expected
