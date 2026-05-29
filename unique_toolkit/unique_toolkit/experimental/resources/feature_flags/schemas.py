from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class FlagEvaluation:
    """Result of a feature flag evaluation.

    ``reason`` indicates how the value was determined:
    - ``"remote"``   — freshly fetched from configuration-backend.
    - ``"cached"``   — served from the in-process TTL cache.
    - ``"stale"``    — transport error; last-known-good value for this flag+company used.
    - ``"fallback"`` — transport error and no prior value; env-var default used.
    """

    value: bool
    reason: Literal["remote", "cached", "stale", "fallback"]
