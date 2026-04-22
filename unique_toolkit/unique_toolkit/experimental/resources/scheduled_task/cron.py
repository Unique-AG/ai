"""Convenience catalogue of 5-field (UTC) cron strings for scheduled tasks.

The server stores schedules as plain cron strings. :class:`Cron` is a
:class:`~enum.StrEnum` of the most common schedules — every member *is* a
``str``, so you can drop it straight into :meth:`ScheduledTasks.create`
without any conversion. For schedules that aren't covered, pass a raw cron
string.

.. note::

    All expressions are interpreted in **UTC** by the server.

.. warning::

    **Experimental.** Ships under :mod:`unique_toolkit.experimental`. API may
    change without notice.

Example
-------

    >>> from unique_toolkit.experimental.resources.scheduled_task import Cron
    >>> Cron.DAILY_MIDNIGHT
    <Cron.DAILY_MIDNIGHT: '0 0 * * *'>
    >>> str(Cron.DAILY_MIDNIGHT)
    '0 0 * * *'
"""

from __future__ import annotations

from enum import StrEnum


class Cron(StrEnum):
    """Named ready-made 5-field cron expressions (UTC).

    Each member is a ``str`` subclass, so instances can be passed straight
    through to anything expecting a cron string — including
    :meth:`ScheduledTasks.create`.
    """

    EVERY_MINUTE = "* * * * *"
    """Fires every minute."""

    EVERY_FIVE_MINUTES = "*/5 * * * *"
    """Fires every 5 minutes."""

    EVERY_FIFTEEN_MINUTES = "*/15 * * * *"
    """Fires every 15 minutes."""

    EVERY_THIRTY_MINUTES = "*/30 * * * *"
    """Fires every 30 minutes."""

    HOURLY = "0 * * * *"
    """Fires once an hour on the hour (``:00``)."""

    DAILY_MIDNIGHT = "0 0 * * *"
    """Fires once a day at 00:00 UTC."""

    DAILY_NOON = "0 12 * * *"
    """Fires once a day at 12:00 UTC."""

    DAILY_9AM = "0 9 * * *"
    """Fires once a day at 09:00 UTC."""

    WEEKDAYS_9AM = "0 9 * * 1-5"
    """Fires on weekdays (Mon-Fri) at 09:00 UTC."""

    WEEKDAYS_MIDNIGHT = "0 0 * * 1-5"
    """Fires on weekdays (Mon-Fri) at 00:00 UTC."""

    WEEKENDS_MIDNIGHT = "0 0 * * 0,6"
    """Fires on weekends (Sat & Sun) at 00:00 UTC."""

    WEEKLY_SUNDAY_MIDNIGHT = "0 0 * * 0"
    """Fires every Sunday at 00:00 UTC."""

    WEEKLY_MONDAY_MIDNIGHT = "0 0 * * 1"
    """Fires every Monday at 00:00 UTC."""

    MONTHLY_FIRST_MIDNIGHT = "0 0 1 * *"
    """Fires on the 1st of every month at 00:00 UTC."""

    MONTHLY_FIFTEENTH_MIDNIGHT = "0 0 15 * *"
    """Fires on the 15th of every month at 00:00 UTC."""

    YEARLY_JAN_FIRST = "0 0 1 1 *"
    """Fires on January 1st at 00:00 UTC."""


__all__ = ["Cron"]
