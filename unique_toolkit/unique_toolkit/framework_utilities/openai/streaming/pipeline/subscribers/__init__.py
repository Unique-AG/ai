"""Default subscribers wired to :data:`StreamEvent`."""

from __future__ import annotations

from .message_persister import MessagePersistingSubscriber

__all__ = ["MessagePersistingSubscriber"]
