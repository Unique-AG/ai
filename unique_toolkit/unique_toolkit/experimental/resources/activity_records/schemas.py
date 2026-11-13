"""Activity Records event model, mirroring the zod schema the service validates with: it
rejects a whole batch if one event fails. Extra keys are forbidden on every path. The
constructor and plain ``model_validate`` accept both the camelCase wire keys and the
Python field names (the toolkit convention); ``ActivityCloudEvent.from_wire`` accepts only
the wire keys, like zod. Experimental: the shape may still change."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Annotated, Any, Final, Literal, Self
from uuid import UUID, uuid4

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    Field,
    JsonValue,
    StringConstraints,
    field_serializer,
    model_validator,
)

from unique_toolkit._common.pydantic_helpers import get_configuration_dict

ACTIVITY_METADATA_MAX_LENGTH: Final = {"identifier": 128, "ip": 64, "text": 256}

_model_config = get_configuration_dict(extra="forbid")
_NIL_UUID: Final = UUID(int=0)
_MAX_UUID: Final = UUID(int=2**128 - 1)


def _is_zod_uuid(value: UUID) -> UUID:
    # zod's z.uuid(): versions 1 to 8 with the RFC variant, plus the nil and max UUIDs.
    if value in (_NIL_UUID, _MAX_UUID) or (value.version or 0) in range(1, 9):
        return value
    raise ValueError("must be a UUID of version 1 to 8")


def _max_length(limit: int) -> AfterValidator:
    # zod counts UTF-16 code units, Python counts code points.
    def check(value: str) -> str:
        if len(value.encode("utf-16-le", "surrogatepass")) > 2 * limit:
            raise ValueError(f"must be at most {limit} characters")
        return value

    return AfterValidator(check)


_NonEmpty = Annotated[str, StringConstraints(strict=True, min_length=1)]
_Identifier = Annotated[
    _NonEmpty, _max_length(ACTIVITY_METADATA_MAX_LENGTH["identifier"])
]
_Ip = Annotated[_NonEmpty, _max_length(ACTIVITY_METADATA_MAX_LENGTH["ip"])]
_Text = Annotated[_NonEmpty, _max_length(ACTIVITY_METADATA_MAX_LENGTH["text"])]


class ActivityActor(BaseModel):
    """Mirrors ``CloudEventActorSchema``."""

    model_config = _model_config

    id: _Identifier
    type: Literal["user", "service"]
    ip: _Ip | None = None


class ActivityAgent(BaseModel):
    """Mirrors ``CloudEventAgentSchema``: the assistant or space the action ran in."""

    model_config = _model_config

    id: _Identifier


class ActivityEventData(BaseModel):
    """Mirrors ``CloudEventDataSchema``."""

    model_config = _model_config

    actor: ActivityActor
    agent: ActivityAgent | None = None
    company_id: _NonEmpty
    target_type: _Identifier | None = None
    target_id: _Identifier | None = None
    target_name: _Text | None = None
    subtype: _Text | None = None
    correlation_id: _Identifier | None = None
    critical_data: dict[str, JsonValue] | None = None

    @model_validator(mode="after")
    def _target_set_together(self) -> ActivityEventData:
        if (self.target_type is None) != (self.target_id is None):
            raise ValueError("target_type and target_id must be set together")
        return self


class ActivityCloudEvent(BaseModel):
    """Mirrors ``CloudEventSchema``: the CloudEvents 1.0 envelope the ingest accepts.

    Extra keys are always forbidden. The constructor and ``model_validate`` accept wire keys
    and Python field names; ``from_wire`` is the strict wire check, used for stored payloads."""

    model_config = _model_config

    specversion: Literal["1.0"] = "1.0"
    id: Annotated[UUID, AfterValidator(_is_zod_uuid)] = Field(default_factory=uuid4)
    # "_" separates source and event id in the service's ``{source}_{id}`` record id.
    source: Annotated[str, StringConstraints(strict=True, pattern=r"^[^:_]+$")]
    type: _NonEmpty
    time: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    datacontenttype: Literal["application/json"] | None = "application/json"
    data: ActivityEventData

    @field_serializer("time")
    def _serialize_time(self, value: datetime) -> str:
        # Same shape as JS ``toISOString()``; the service schema rejects ``+00:00``.
        return (
            value.astimezone(UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )

    @classmethod
    def from_wire(cls, payload: Mapping[str, Any]) -> Self:
        """Validate a wire dict like zod does: camelCase keys only, no Python field names."""
        return cls.model_validate(payload, by_alias=True, by_name=False)

    def to_wire(self) -> dict[str, Any]:
        """JSON-ready dict in the camelCase wire format, without ``None`` fields."""
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)
