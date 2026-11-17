"""Activity Records settings: size limits."""

from __future__ import annotations

from typing import Final, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from unique_toolkit.experimental.resources.activity_records.json_size import (
    json_byte_length,
)
from unique_toolkit.experimental.resources.activity_records.schemas import (
    ACTIVITY_METADATA_MAX_LENGTH,
)

DEFAULT_MAX_DATA_SIZE_BYTES: Final = 1_048_576
DEFAULT_MAX_BATCH_SIZE_BYTES: Final = 8_388_608
FEATURE_FLAG_ENABLE_ACTIVITY_RECORDS_EVENTS_UN_22616: Final = (
    "FEATURE_FLAG_ENABLE_ACTIVITY_RECORDS_EVENTS_UN_22616"
)
OUTBOX_MAX_BACKOFF_ATTEMPTS: Final = 11
DEFAULT_ACTIVITY_EVENTS_METRIC_NAME: Final = "unique_activity_events_total"
ACTIVITY_RECORDS_INSTALL_HINT: Final = (
    "Install it with: uv add 'unique-toolkit[activity-records]'"
)

_MAX_SAFE_INTEGER: Final = 2**53 - 1


_identifier = "x" * ACTIVITY_METADATA_MAX_LENGTH["identifier"]
_text = "x" * ACTIVITY_METADATA_MAX_LENGTH["text"]

# Worst case ``data``: every metadata field at its cap and ``criticalData`` shrunk to its shell.
MIN_MAX_DATA_SIZE_BYTES: Final = json_byte_length(
    {
        "actor": {
            "id": _identifier,
            "type": "service",
            "ip": "x" * ACTIVITY_METADATA_MAX_LENGTH["ip"],
        },
        "agent": {"id": _identifier},
        "companyId": _identifier,
        "targetType": _identifier,
        "targetId": _identifier,
        "targetName": _text,
        "subtype": _text,
        "correlationId": _identifier,
        "criticalData": {
            "truncated": True,
            "originalSizeBytesAtLeast": _MAX_SAFE_INTEGER,
            "maxDataSizeBytes": _MAX_SAFE_INTEGER,
            "value": None,
        },
    }
)

# Envelope fields outside ``data`` plus punctuation. ``source`` and ``type`` are uncapped,
# so this is a generous allowance, not an exact one.
EVENT_ENVELOPE_RESERVE_BYTES: Final = (
    json_byte_length(
        {
            "specversion": "1.0",
            "id": "00000000-0000-0000-0000-000000000000",
            "source": "x" * 128,
            "type": "x" * 128,
            "time": "2026-01-01T00:00:00.000Z",
            "datacontenttype": "application/json",
        }
    )
    + 2
)


class ActivityRecordsConfig(BaseSettings):
    """Read from ``ACTIVITY_RECORDS_MAX_DATA_SIZE_BYTES`` and ``ACTIVITY_RECORDS_MAX_BATCH_SIZE_BYTES``."""

    model_config = SettingsConfigDict(
        env_prefix="ACTIVITY_RECORDS_", extra="ignore", hide_input_in_errors=True
    )

    max_data_size_bytes: int = Field(
        default=DEFAULT_MAX_DATA_SIZE_BYTES, ge=MIN_MAX_DATA_SIZE_BYTES
    )
    max_batch_size_bytes: int = DEFAULT_MAX_BATCH_SIZE_BYTES

    @model_validator(mode="after")
    def _one_event_fits_a_batch(self) -> Self:
        minimum = self.max_data_size_bytes + EVENT_ENVELOPE_RESERVE_BYTES
        if self.max_batch_size_bytes < minimum:
            raise ValueError(
                f"max_batch_size_bytes ({self.max_batch_size_bytes}) must be at least "
                f"max_data_size_bytes plus the envelope reserve ({minimum}), so one "
                "maximally-sized event always fits a batch by itself"
            )
        return self
