"""Pydantic schemas for the :mod:`unique_toolkit.experimental.resources.groups` resource.

Mirrors :mod:`unique_sdk.Group` responses with field-level documentation and
camelCase aliases so SDK wire payloads validate directly via
:func:`BaseModel.model_validate`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from humps import camelize
from pydantic import BaseModel, ConfigDict, Field

_model_config = ConfigDict(
    alias_generator=camelize,
    populate_by_name=True,
)


class GroupMember(BaseModel):
    """A single member entry as returned on :class:`GroupInfo.members`."""

    model_config = _model_config

    entity_id: str = Field(
        description=(
            "The user id of this member. Named ``entity_id`` in the API because the "
            "member model allows non-user principals in future revisions."
        ),
    )


class GroupInfo(BaseModel):
    """Directory record for a group (``GET /groups``).

    A group is the Unique equivalent of a POSIX group: an addressable set of
    users that can be granted permissions collectively (see the folder ACL
    model). Groups may be nested via :attr:`parent_id`.
    """

    model_config = _model_config

    id: str = Field(description="Group id; primary key.")
    name: str = Field(description="Display name. Unique within the company.")
    external_id: str | None = Field(
        default=None,
        description="Upstream directory id (SCIM/SSO) or ``None`` for local groups.",
    )
    parent_id: str | None = Field(
        default=None,
        description=(
            "Parent group id when the group is nested; ``None`` for top-level groups."
        ),
    )
    members: list[GroupMember] | None = Field(
        default=None,
        description=(
            "Group members. The list endpoint (``list_groups``) returns ``None`` "
            "to keep the response small; membership is only materialised on the "
            "single-group detail endpoints."
        ),
    )
    created_at: datetime = Field(description="When the group was created.")
    updated_at: datetime = Field(description="When the group was last mutated.")


class GroupWithConfiguration(GroupInfo):
    """A :class:`GroupInfo` plus the free-form ``configuration`` blob."""

    model_config = _model_config

    configuration: dict[str, Any] = Field(
        description=(
            "Free-form per-group configuration blob. The schema is application-"
            "defined; the platform treats it as opaque JSON."
        ),
    )


class GroupMembership(BaseModel):
    """Relationship row between a user (``entity_id``) and a group (``group_id``)."""

    model_config = _model_config

    entity_id: str = Field(description="User id on the user side of the relationship.")
    group_id: str = Field(description="Group id on the group side of the relationship.")
    created_at: datetime = Field(description="When the membership was created.")


class GroupDeleted(BaseModel):
    """Response from ``delete_group`` — echoes the deleted group's id."""

    model_config = _model_config

    id: str = Field(description="Id of the group that was deleted.")
