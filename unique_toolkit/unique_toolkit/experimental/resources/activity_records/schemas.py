"""Activity Records event model, mirroring the zod schema the service validates with: it
rejects a whole batch if one event fails. Extra keys are forbidden on every path. The
constructor and plain ``model_validate`` accept both the camelCase wire keys and the
Python field names (the toolkit convention); ``ActivityCloudEvent.from_wire`` accepts only
the wire keys, like zod. ``ActivityCloudEvent.build`` can shorten over-length metadata.
Experimental: the shape may still change."""

from __future__ import annotations

import re
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
    PrivateAttr,
    StringConstraints,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
    WrapValidator,
    field_serializer,
    model_validator,
)
from pydantic.alias_generators import to_camel

from unique_toolkit._common.pydantic_helpers import get_configuration_dict
from unique_toolkit.experimental.resources.activity_records.json_size import (
    truncate_to_utf16_length,
)

ACTIVITY_METADATA_MAX_LENGTH: Final = {"identifier": 128, "ip": 64, "text": 256}

_model_config = get_configuration_dict(extra="forbid")
# Same replacement as prepare.py: pydantic and Postgres both reject a lone surrogate.
_LONE_SURROGATE = re.compile("[\ud800-\udfff]")
_NIL_UUID: Final = UUID(int=0)
_MAX_UUID: Final = UUID(int=2**128 - 1)


def _is_zod_uuid(value: UUID) -> UUID:
    # zod's z.uuid(): versions 1 to 8 with the RFC variant, plus the nil and max UUIDs.
    if value in (_NIL_UUID, _MAX_UUID) or (value.version or 0) in range(1, 9):
        return value
    raise ValueError("must be a UUID of version 1 to 8")


def _max_length(limit: int, path: str | None = None) -> WrapValidator:
    # zod counts UTF-16 code units, Python counts code points. With ``truncate`` set in the
    # validation context, lone surrogates are replaced and over-length values cut and recorded.
    def check(
        value: Any, handler: ValidatorFunctionWrapHandler, info: ValidationInfo
    ) -> str:
        context = info.context or {}
        if context.get("truncate") and isinstance(value, str):
            value = _LONE_SURROGATE.sub("\ufffd", value)
            cut = truncate_to_utf16_length(value, limit)
            if cut != value:
                # Wire path like Node (actor.id, targetName); a bare field name when unset.
                context.get("truncated", []).append(
                    path or to_camel(info.field_name or "")
                )
                value = cut
        result = handler(value)
        if len(result.encode("utf-16-le", "surrogatepass")) > 2 * limit:
            raise ValueError(f"must be at most {limit} characters")
        return result

    return WrapValidator(check)


_NonEmpty = Annotated[str, StringConstraints(strict=True, min_length=1)]
_Identifier = Annotated[
    _NonEmpty, _max_length(ACTIVITY_METADATA_MAX_LENGTH["identifier"])
]
_Text = Annotated[_NonEmpty, _max_length(ACTIVITY_METADATA_MAX_LENGTH["text"])]
_ActorId = Annotated[
    _NonEmpty, _max_length(ACTIVITY_METADATA_MAX_LENGTH["identifier"], "actor.id")
]
_ActorIp = Annotated[
    _NonEmpty, _max_length(ACTIVITY_METADATA_MAX_LENGTH["ip"], "actor.ip")
]
_AgentId = Annotated[
    _NonEmpty, _max_length(ACTIVITY_METADATA_MAX_LENGTH["identifier"], "agent.id")
]


class ActivityActor(BaseModel):
    """Mirrors ``CloudEventActorSchema``."""

    model_config = _model_config

    id: _ActorId
    type: Literal["user", "service"]
    ip: _ActorIp | None = None


class ActivityAgent(BaseModel):
    """Mirrors ``CloudEventAgentSchema``: the assistant or space the action ran in."""

    model_config = _model_config

    id: _AgentId


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
    _truncated_fields: list[str] = PrivateAttr(default_factory=list)

    @classmethod
    def build(cls, **fields: Any) -> Self:
        """Validate ``fields`` (``data`` as a dict) like the constructor, but shorten
        over-length metadata instead of rejecting it. See ``truncated_fields``."""
        truncated: list[str] = []
        event = cls.model_validate(
            fields, context={"truncate": True, "truncated": truncated}
        )
        event._truncated_fields = truncated
        return event

    @property
    def truncated_fields(self) -> list[str]:
        """Names of the metadata fields ``build`` shortened; empty otherwise."""
        return self._truncated_fields

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
