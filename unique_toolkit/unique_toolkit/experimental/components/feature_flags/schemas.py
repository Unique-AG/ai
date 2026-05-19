from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class FlagEvaluation:
    """Result of a feature flag evaluation.

    Attributes:
        value: The boolean value of the flag.
        reason: How the value was determined.
            - ``"remote"``   — freshly fetched from configuration-backend.
            - ``"cached"``   — returned from the in-process TTL cache.
            - ``"fallback"`` — transport error or client unavailable; env-var used.
            - ``"default"``  — reserved for future use (e.g. unknown flag key).
    """

    value: bool
    reason: Literal["remote", "cached", "fallback", "default"]
