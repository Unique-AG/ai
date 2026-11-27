"""Behavioral interfaces for the Activity Records outbox."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

from unique_toolkit.experimental.resources.activity_records.prepare import WireEvent

if TYPE_CHECKING:
    from unique_toolkit.experimental.resources.feature_flags.schemas import (
        FlagEvaluation,
    )


class PublisherLike(Protocol):
    async def publish(self, events: Sequence[WireEvent]) -> None: ...


class FlagClientLike(Protocol):
    async def evaluate(self, flag: str, *, company_id: str) -> FlagEvaluation: ...
