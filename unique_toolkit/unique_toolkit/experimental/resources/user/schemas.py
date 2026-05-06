"""Pydantic schemas for the :mod:`unique_toolkit.experimental.resources.user` resource.

Mirrors :mod:`unique_sdk.User` responses with field-level documentation and
camelCase aliases so SDK wire payloads validate directly via
:func:`BaseModel.model_validate`. :class:`UserGroupMembership` is the response
shape of ``GET /users/{id}/groups`` and lives here — not in
:mod:`..group.schemas` — because the endpoint is rooted on the user.
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
    """One of the groups a user is a member of (``GET /users/{id}/groups``).

    This is the response shape of a *user* endpoint — a subset of
    :class:`~unique_toolkit.experimental.resources.group.schemas.GroupInfo`
    with no ``members`` or ``configuration`` field — and therefore lives with
    the users resource, not the groups resource.
    """

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
