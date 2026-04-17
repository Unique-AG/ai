"""Unit tests for :class:`unique_toolkit.experimental.identity.Identity`.

All SDK calls are mocked via ``pytest-mock`` so the tests never hit the network.
Each test exercises one behaviour of ``Identity`` and asserts both the return
value shape (Pydantic validation works) and the exact parameters forwarded to
``unique_sdk``.
"""

from __future__ import annotations

from typing import Any

import pytest

from unique_toolkit.experimental.identity import (
    GroupDeleted,
    GroupInfo,
    GroupMembership,
    Identity,
    UserGroupMembership,
    UserInfo,
    UserWithConfiguration,
)

USER_ID = "acting-user"
COMPANY_ID = "acting-company"


@pytest.fixture
def identity() -> Identity:
    """Provide an :class:`Identity` bound to a fixed ``(user_id, company_id)``."""
    return Identity(company_id=COMPANY_ID, user_id=USER_ID)


def _user_payload(**overrides: Any) -> dict[str, Any]:
    """Return a minimal valid user payload (wire shape, camelCase)."""
    payload: dict[str, Any] = {
        "id": "u-1",
        "externalId": "ext-1",
        "firstName": "Ada",
        "lastName": "Lovelace",
        "displayName": "Ada Lovelace",
        "userName": "ada",
        "email": "ada@example.com",
        "active": True,
        "createdAt": "2025-01-01T00:00:00Z",
        "updatedAt": "2025-01-02T00:00:00Z",
    }
    payload.update(overrides)
    return payload


def _group_payload(**overrides: Any) -> dict[str, Any]:
    """Return a minimal valid group payload (wire shape, camelCase)."""
    payload: dict[str, Any] = {
        "id": "g-1",
        "name": "engineers",
        "externalId": None,
        "parentId": None,
        "members": None,
        "createdAt": "2025-01-01T00:00:00Z",
        "updatedAt": "2025-01-02T00:00:00Z",
    }
    payload.update(overrides)
    return payload


# ── Users ─────────────────────────────────────────────────────────────────────


class TestAIListUsers:
    def test_AI_list_users_returns_validated_models(self, identity, mocker):
        """list_users should forward optional filters and return UserInfo models."""
        mock = mocker.patch(
            "unique_toolkit.experimental.identity.functions.unique_sdk.User.get_users",
            return_value={"users": [_user_payload()]},
        )

        result = identity.list_users(email="ada@example.com", take=10)

        assert len(result) == 1
        assert isinstance(result[0], UserInfo)
        assert result[0].email == "ada@example.com"
        mock.assert_called_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            email="ada@example.com",
            take=10,
        )

    @pytest.mark.asyncio
    async def test_AI_list_users_async_delegates_to_async_sdk(self, identity, mocker):
        """list_users_async must call the async SDK variant, not the sync one."""
        mock = mocker.patch(
            "unique_toolkit.experimental.identity.functions.unique_sdk.User.get_users_async",
            return_value={"users": []},
        )

        result = await identity.list_users_async(skip=5)

        assert result == []
        mock.assert_called_once_with(user_id=USER_ID, company_id=COMPANY_ID, skip=5)


class TestAIGetUser:
    def test_AI_get_user_by_id_hits_id_endpoint(self, identity, mocker):
        """get_user(user_id=...) should call the /users/{id} endpoint."""
        mock = mocker.patch(
            "unique_toolkit.experimental.identity.functions.unique_sdk.User.get_by_id",
            return_value=_user_payload(id="u-42"),
        )

        user = identity.get_user(user_id="u-42")

        assert user.id == "u-42"
        mock.assert_called_once_with(
            user_id=USER_ID, company_id=COMPANY_ID, target_user_id="u-42"
        )

    def test_AI_get_user_by_email_resolves_through_list(self, identity, mocker):
        """get_user(email=...) should resolve via a filtered list and return the single match."""
        mock = mocker.patch(
            "unique_toolkit.experimental.identity.functions.unique_sdk.User.get_users",
            return_value={"users": [_user_payload(email="ada@example.com")]},
        )

        user = identity.get_user(email="ada@example.com")

        assert user.email == "ada@example.com"
        mock.assert_called_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            email="ada@example.com",
            take=2,
        )

    def test_AI_get_user_with_no_identifier_raises_type_error(self, identity):
        """get_user() with no identifier must raise TypeError (overload contract)."""
        with pytest.raises(TypeError, match="exactly one of"):
            identity.get_user()

    def test_AI_get_user_with_multiple_identifiers_raises_type_error(self, identity):
        """Mixing two identifiers is a contract violation."""
        with pytest.raises(TypeError, match="exactly one of"):
            identity.get_user(user_id="u-1", email="ada@example.com")

    def test_AI_get_user_by_email_no_match_raises_lookup_error(self, identity, mocker):
        """A unique filter returning zero rows should surface as LookupError."""
        mocker.patch(
            "unique_toolkit.experimental.identity.functions.unique_sdk.User.get_users",
            return_value={"users": []},
        )

        with pytest.raises(LookupError, match="no user matches"):
            identity.get_user(email="ghost@example.com")

    def test_AI_get_user_by_email_multiple_matches_raises_lookup_error(
        self, identity, mocker
    ):
        """Ambiguous matches must be surfaced, not silently collapsed to the first."""
        mocker.patch(
            "unique_toolkit.experimental.identity.functions.unique_sdk.User.get_users",
            return_value={
                "users": [
                    _user_payload(id="u-1", email="dup@example.com"),
                    _user_payload(id="u-2", email="dup@example.com"),
                ]
            },
        )

        with pytest.raises(LookupError, match="2 users match"):
            identity.get_user(email="dup@example.com")


class TestAIGroupsOf:
    def test_AI_groups_of_by_user_id(self, identity, mocker):
        """groups_of(user_id=...) should call /users/{id}/groups directly."""
        mock = mocker.patch(
            "unique_toolkit.experimental.identity.functions.unique_sdk.User.get_user_groups",
            return_value={
                "groups": [
                    {
                        "id": "g-1",
                        "name": "engineers",
                        "externalId": None,
                        "parentId": None,
                        "createdAt": "2025-01-01T00:00:00Z",
                        "updatedAt": "2025-01-02T00:00:00Z",
                    }
                ]
            },
        )

        memberships = identity.groups_of(user_id="u-42")

        assert len(memberships) == 1
        assert isinstance(memberships[0], UserGroupMembership)
        assert memberships[0].id == "g-1"
        mock.assert_called_once_with(
            user_id=USER_ID, company_id=COMPANY_ID, target_user_id="u-42"
        )

    def test_AI_is_member_true_when_group_in_list(self, identity, mocker):
        """is_member returns True when the target group appears in groups_of."""
        mocker.patch(
            "unique_toolkit.experimental.identity.functions.unique_sdk.User.get_user_groups",
            return_value={
                "groups": [
                    {
                        "id": "g-1",
                        "name": "engineers",
                        "externalId": None,
                        "parentId": None,
                        "createdAt": "2025-01-01T00:00:00Z",
                        "updatedAt": "2025-01-02T00:00:00Z",
                    }
                ]
            },
        )

        assert identity.is_member(user_id="u-42", group_id="g-1") is True

    def test_AI_is_member_false_when_group_missing(self, identity, mocker):
        """is_member returns False when the target group is not in the list."""
        mocker.patch(
            "unique_toolkit.experimental.identity.functions.unique_sdk.User.get_user_groups",
            return_value={"groups": []},
        )

        assert identity.is_member(user_id="u-42", group_id="g-1") is False


class TestAIUpdateUserConfiguration:
    def test_AI_update_user_configuration_defaults_target_to_self(
        self, identity, mocker
    ):
        """Omitting target_user_id must default to the acting user."""
        mock = mocker.patch(
            "unique_toolkit.experimental.identity.functions.unique_sdk.User.update_user_configuration",
            return_value={
                **_user_payload(id=USER_ID),
                "userConfiguration": {"theme": "dark"},
            },
        )

        user = identity.update_user_configuration(configuration={"theme": "dark"})

        assert isinstance(user, UserWithConfiguration)
        assert user.user_configuration == {"theme": "dark"}
        mock.assert_called_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            userConfiguration={"theme": "dark"},
        )


# ── Groups ────────────────────────────────────────────────────────────────────


class TestAIListGroups:
    def test_AI_list_groups_forwards_name_filter(self, identity, mocker):
        """list_groups should forward the name filter to the SDK."""
        mock = mocker.patch(
            "unique_toolkit.experimental.identity.functions.unique_sdk.Group.get_groups",
            return_value={"groups": [_group_payload()]},
        )

        groups = identity.list_groups(name="engineers")

        assert len(groups) == 1
        assert isinstance(groups[0], GroupInfo)
        mock.assert_called_once_with(
            user_id=USER_ID, company_id=COMPANY_ID, name="engineers"
        )


class TestAICreateGroup:
    def test_AI_create_group_minimum_params_sends_only_name(self, identity, mocker):
        """Optional parent_id / external_id must not appear when omitted."""
        mock = mocker.patch(
            "unique_toolkit.experimental.identity.functions.unique_sdk.Group.create_group",
            return_value=_group_payload(name="new-team"),
        )

        group = identity.create_group(name="new-team")

        assert group.name == "new-team"
        mock.assert_called_once_with(
            user_id=USER_ID, company_id=COMPANY_ID, name="new-team"
        )

    def test_AI_create_group_with_parent_forwards_camel_case(self, identity, mocker):
        """parent_id/external_id must be serialised to camelCase on the wire."""
        mock = mocker.patch(
            "unique_toolkit.experimental.identity.functions.unique_sdk.Group.create_group",
            return_value=_group_payload(
                id="g-2", name="sub-team", parentId="g-1", externalId="ext-2"
            ),
        )

        group = identity.create_group(
            name="sub-team", parent_id="g-1", external_id="ext-2"
        )

        assert group.parent_id == "g-1"
        assert group.external_id == "ext-2"
        mock.assert_called_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            name="sub-team",
            parentId="g-1",
            externalId="ext-2",
        )


class TestAIDeleteGroup:
    def test_AI_delete_group_returns_group_deleted(self, identity, mocker):
        """delete_group returns GroupDeleted with the deleted id."""
        mock = mocker.patch(
            "unique_toolkit.experimental.identity.functions.unique_sdk.Group.delete_group",
            return_value={"id": "g-1"},
        )

        result = identity.delete_group("g-1")

        assert isinstance(result, GroupDeleted)
        assert result.id == "g-1"
        mock.assert_called_once_with(
            user_id=USER_ID, company_id=COMPANY_ID, group_id="g-1"
        )


class TestAIRenameGroup:
    def test_AI_rename_group_calls_update_with_new_name(self, identity, mocker):
        """rename_group maps to SDK update_group(name=new_name)."""
        mock = mocker.patch(
            "unique_toolkit.experimental.identity.functions.unique_sdk.Group.update_group",
            return_value=_group_payload(name="renamed"),
        )

        group = identity.rename_group("g-1", new_name="renamed")

        assert group.name == "renamed"
        mock.assert_called_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            group_id="g-1",
            name="renamed",
        )


class TestAIMembership:
    def test_AI_add_members_returns_membership_list(self, identity, mocker):
        """add_members returns GroupMembership models for each new row."""
        mock = mocker.patch(
            "unique_toolkit.experimental.identity.functions.unique_sdk.Group.add_users_to_group",
            return_value={
                "memberships": [
                    {
                        "entityId": "u-1",
                        "groupId": "g-1",
                        "createdAt": "2025-01-01T00:00:00Z",
                    },
                    {
                        "entityId": "u-2",
                        "groupId": "g-1",
                        "createdAt": "2025-01-01T00:00:00Z",
                    },
                ]
            },
        )

        memberships = identity.add_members("g-1", user_ids=["u-1", "u-2"])

        assert len(memberships) == 2
        assert all(isinstance(m, GroupMembership) for m in memberships)
        mock.assert_called_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            group_id="g-1",
            userIds=["u-1", "u-2"],
        )

    def test_AI_add_members_with_empty_list_raises(self, identity, mocker):
        """Empty user_ids must be rejected client-side to avoid a no-op API call."""
        mocker.patch(
            "unique_toolkit.experimental.identity.functions.unique_sdk.Group.add_users_to_group"
        )

        with pytest.raises(ValueError, match="must not be empty"):
            identity.add_members("g-1", user_ids=[])

    def test_AI_remove_members_returns_success_bool(self, identity, mocker):
        """remove_members returns the raw success flag from the API."""
        mocker.patch(
            "unique_toolkit.experimental.identity.functions.unique_sdk.Group.remove_users_from_group",
            return_value={"success": True},
        )

        assert identity.remove_members("g-1", user_ids=["u-1"]) is True

    @pytest.mark.asyncio
    async def test_AI_remove_members_async_delegates_to_async_sdk(
        self, identity, mocker
    ):
        """Async variant must call the async SDK method."""
        mock = mocker.patch(
            "unique_toolkit.experimental.identity.functions.unique_sdk.Group.remove_users_from_group_async",
            return_value={"success": False},
        )

        result = await identity.remove_members_async("g-1", user_ids=["u-1"])

        assert result is False
        mock.assert_called_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            group_id="g-1",
            userIds=["u-1"],
        )


# ── Construction ──────────────────────────────────────────────────────────────


class TestAIConstruction:
    def test_AI_init_with_missing_values_raises(self):
        """Identity must reject None company/user ids (validate_required_values)."""
        with pytest.raises(ValueError, match="Required values cannot be None"):
            Identity(company_id=None, user_id=USER_ID)  # type: ignore[arg-type]
