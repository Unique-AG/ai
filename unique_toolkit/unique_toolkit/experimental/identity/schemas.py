"""Pydantic schemas for the identity (users & groups) subpackage.

These models mirror the :mod:`unique_sdk.User` and :mod:`unique_sdk.Group` TypedDicts
but add:

- field-level documentation (``Field(..., description=...)``) so the intent of each
  attribute is visible in IDEs, the docs site, and `help(...)`;
- camelCase aliases so the SDK's wire payload (``createdAt``, ``parentId``, …) can be
  validated directly via :func:`BaseModel.model_validate`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from humps import camelize
from pydantic import BaseModel, ConfigDict, Field

_model_config = ConfigDict(
    alias_generator=camelize,
    populate_by_name=True,
    arbitrary_types_allowed=True,
)


# ── Users ─────────────────────────────────────────────────────────────────────


class UserInfo(BaseModel):
    """Directory record for a single user (``GET /users/{id}``).

    The ``id`` field is the canonical user id used everywhere in the platform
    (equivalent to ``uid`` on a Linux box). The ``external_id`` is the upstream
    identity-provider id (SSO / SCIM), present on provisioned users, absent on
    users created via the admin UI.
    """

    model_config = _model_config

    id: str = Field(
        description=(
            "Internal user id. Use this when calling any toolkit/SDK method that "
            "takes ``user_id``. Stable for the lifetime of the account."
        ),
    )
    external_id: str | None = Field(
        default=None,
        description=(
            "Upstream identity-provider id (SCIM/SSO). ``None`` for users who were "
            "not provisioned through the directory sync."
        ),
    )
    first_name: str = Field(description="Given name as stored in the directory.")
    last_name: str = Field(description="Family name as stored in the directory.")
    display_name: str = Field(
        description=(
            'Human-readable label. Typically ``f"{first_name} {last_name}"`` but '
            "may be overridden by the directory admin."
        ),
    )
    user_name: str = Field(
        description=(
            "Login handle / username (the ``pw_name`` equivalent). Unique within a "
            "company."
        ),
    )
    email: str = Field(description="Primary contact email. Unique within a company.")
    active: bool = Field(
        description=(
            "``True`` when the user can log in. Set to ``False`` on deprovisioning; "
            "memberships and ACLs are preserved but the user cannot authenticate."
        ),
    )
    created_at: datetime = Field(
        description="When the user record was created (ISO-8601 from the API).",
    )
    updated_at: datetime = Field(
        description="When the user record was last mutated (ISO-8601).",
    )


class UserWithConfiguration(UserInfo):
    """A :class:`UserInfo` plus the free-form ``user_configuration`` blob.

    The configuration blob is an opaque JSON object used by apps and the frontend
    to store per-user preferences. The platform does not interpret it; the
    contract between writer and reader is entirely application-defined.
    """

    model_config = _model_config

    user_configuration: dict[str, Any] = Field(
        description=(
            "Free-form per-user configuration blob. The schema is entirely "
            "application-defined; the platform treats it as opaque JSON."
        ),
    )


class UserGroupMembership(BaseModel):
    """One of the groups a user is a member of (``GET /users/{id}/groups``)."""

    model_config = _model_config

    id: str = Field(description="Group id (``gid`` equivalent).")
    name: str = Field(description="Group display name; unique within the company.")
    external_id: str | None = Field(
        default=None,
        description="Upstream group id (SCIM/SSO) or ``None`` if locally managed.",
    )
    parent_id: str | None = Field(
        default=None,
        description=(
            "Scope id of the parent group when the group hierarchy is nested, "
            "``None`` for top-level groups."
        ),
    )
    created_at: datetime = Field(description="When the group was created.")
    updated_at: datetime = Field(description="When the group was last mutated.")


# ── Groups ────────────────────────────────────────────────────────────────────


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
