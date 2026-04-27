"""Unit tests for the split Identity service (:class:`Users`, :class:`Groups`,
and the :class:`Identity` facade).

All SDK calls are mocked via ``pytest-mock`` so the tests never hit the network.
Each test exercises one behaviour and asserts both the return value shape
(Pydantic validation works) and the exact parameters forwarded to
``unique_sdk``.
"""

from __future__ import annotations

from typing import Any

import pytest

from unique_toolkit.experimental.identity import (
    GroupDeleted,
    GroupInfo,
    GroupMembership,
    Groups,
    Identity,
    UserGroupMembership,
    UserInfo,
    Users,
    UserWithConfiguration,
)

USER_ID = "acting-user"
COMPANY_ID = "acting-company"


@pytest.fixture
def identity() -> Identity:
    """Provide an :class:`Identity` bound to a fixed ``(user_id, company_id)``."""
    return Identity(user_id=USER_ID, company_id=COMPANY_ID)


@pytest.fixture
def users(identity: Identity) -> Users:
    """Sub-service for user-centric tests."""
    return identity.users


@pytest.fixture
def groups(identity: Identity) -> Groups:
    """Sub-service for group-centric tests."""
    return identity.groups


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


# ── Facade wiring ─────────────────────────────────────────────────────────────


class TestAIFacade:
    def test_AI_identity_exposes_users_and_groups_sub_services(self, identity):
        """The facade must wire both sub-services with the same credentials."""
        assert isinstance(identity.users, Users)
        assert isinstance(identity.groups, Groups)
        assert identity.users._user_id == USER_ID
        assert identity.users._company_id == COMPANY_ID
        assert identity.groups._user_id == USER_ID
        assert identity.groups._company_id == COMPANY_ID

    def test_AI_identity_init_is_keyword_only(self):
        """Positional args must be rejected — the init is intentionally kw-only."""
        with pytest.raises(TypeError):
            Identity(USER_ID, COMPANY_ID)  # type: ignore[misc]

    def test_AI_users_init_is_keyword_only(self):
        """``Users`` standalone init is also kw-only."""
        with pytest.raises(TypeError):
            Users(USER_ID, COMPANY_ID)  # type: ignore[misc]

    def test_AI_groups_init_is_keyword_only(self):
        """``Groups`` standalone init is also kw-only."""
        with pytest.raises(TypeError):
            Groups(USER_ID, COMPANY_ID)  # type: ignore[misc]


# ── Users ─────────────────────────────────────────────────────────────────────


class TestAIUsersList:
    def test_AI_list_returns_validated_models(self, users, mocker):
        """users.list forwards optional filters and returns UserInfo models."""
        mock = mocker.patch(
            "unique_toolkit.experimental.resources.user.functions.User.get_users",
            return_value={"users": [_user_payload()]},
        )

        result = users.list(email="ada@example.com", take=10)

        assert len(result) == 1
        assert isinstance(result[0], UserInfo)
        assert result[0].email == "ada@example.com"
        mock.assert_called_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            skip=0,
            take=10,
            email="ada@example.com",
        )

    @pytest.mark.asyncio
    async def test_AI_list_async_delegates_to_async_sdk(self, users, mocker):
        """users.list_async must call the async SDK variant, not the sync one."""
        mock = mocker.patch(
            "unique_toolkit.experimental.resources.user.functions.User.get_users_async",
            return_value={"users": []},
        )

        result = await users.list_async(skip=5)

        assert result == []
        mock.assert_called_once_with(
            user_id=USER_ID, company_id=COMPANY_ID, skip=5, take=100
        )


class TestAIUsersGet:
    def test_AI_get_by_id_hits_id_endpoint(self, users, mocker):
        """users.get(user_id=...) should call the /users/{id} endpoint."""
        mock = mocker.patch(
            "unique_toolkit.experimental.resources.user.functions.User.get_by_id",
            return_value=_user_payload(id="u-42"),
        )

        user = users.get(user_id="u-42")

        assert user.id == "u-42"
        mock.assert_called_once_with(
            user_id=USER_ID, company_id=COMPANY_ID, target_user_id="u-42"
        )

    def test_AI_get_by_email_resolves_through_list(self, users, mocker):
        """users.get(email=...) should resolve via a filtered list and return the single match."""
        mock = mocker.patch(
            "unique_toolkit.experimental.resources.user.functions.User.get_users",
            return_value={"users": [_user_payload(email="ada@example.com")]},
        )

        user = users.get(email="ada@example.com")

        assert user.email == "ada@example.com"
        mock.assert_called_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            skip=0,
            take=2,
            email="ada@example.com",
        )

    def test_AI_get_with_no_identifier_raises_type_error(self, users):
        """users.get() with no identifier must raise TypeError (overload contract)."""
        with pytest.raises(TypeError, match="exactly one of"):
            users.get()

    def test_AI_get_with_multiple_identifiers_raises_type_error(self, users):
        """Mixing two identifiers is a contract violation."""
        with pytest.raises(TypeError, match="exactly one of"):
            users.get(user_id="u-1", email="ada@example.com")

    def test_AI_get_by_email_no_match_raises_lookup_error(self, users, mocker):
        """A unique filter returning zero rows should surface as LookupError."""
        mocker.patch(
            "unique_toolkit.experimental.resources.user.functions.User.get_users",
            return_value={"users": []},
        )

        with pytest.raises(LookupError, match="no user matches"):
            users.get(email="ghost@example.com")

    def test_AI_get_by_email_multiple_matches_raises_lookup_error(self, users, mocker):
        """Ambiguous matches must be surfaced, not silently collapsed to the first."""
        mocker.patch(
            "unique_toolkit.experimental.resources.user.functions.User.get_users",
            return_value={
                "users": [
                    _user_payload(id="u-1", email="dup@example.com"),
                    _user_payload(id="u-2", email="dup@example.com"),
                ]
            },
        )

        with pytest.raises(LookupError, match="2 users match"):
            users.get(email="dup@example.com")


class TestAIUsersGroupsOf:
    def test_AI_groups_of_by_user_id(self, users, mocker):
        """groups_of(user_id=...) should call /users/{id}/groups directly."""
        mock = mocker.patch(
            "unique_toolkit.experimental.resources.user.functions.User.get_user_groups",
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

        memberships = users.groups_of(user_id="u-42")

        assert len(memberships) == 1
        assert isinstance(memberships[0], UserGroupMembership)
        assert memberships[0].id == "g-1"
        mock.assert_called_once_with(
            user_id=USER_ID, company_id=COMPANY_ID, target_user_id="u-42"
        )

    def test_AI_is_member_true_when_group_in_list(self, users, mocker):
        """is_member returns True when the target group appears in groups_of."""
        mocker.patch(
            "unique_toolkit.experimental.resources.user.functions.User.get_user_groups",
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

        assert users.is_member(user_id="u-42", group_id="g-1") is True

    def test_AI_is_member_false_when_group_missing(self, users, mocker):
        """is_member returns False when the target group is not in the list."""
        mocker.patch(
            "unique_toolkit.experimental.resources.user.functions.User.get_user_groups",
            return_value={"groups": []},
        )

        assert users.is_member(user_id="u-42", group_id="g-1") is False


class TestAIUsersUpdateConfiguration:
    def test_AI_update_configuration_defaults_target_to_self(self, users, mocker):
        """Omitting target_user_id must default to the acting user."""
        mock = mocker.patch(
            "unique_toolkit.experimental.resources.user.functions.User.update_user_configuration",
            return_value={
                **_user_payload(id=USER_ID),
                "userConfiguration": {"theme": "dark"},
            },
        )

        user = users.update_configuration(configuration={"theme": "dark"})

        assert isinstance(user, UserWithConfiguration)
        assert user.user_configuration == {"theme": "dark"}
        mock.assert_called_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            userConfiguration={"theme": "dark"},
        )

    def test_AI_update_configuration_rejects_other_target(self, users, mocker):
        """Passing target_user_id != self must raise instead of silently swapping."""
        mock = mocker.patch(
            "unique_toolkit.experimental.resources.user.functions.User.update_user_configuration"
        )

        with pytest.raises(ValueError, match="target_user_id must equal user_id"):
            users.update_configuration(
                configuration={"theme": "dark"}, target_user_id="someone-else"
            )

        mock.assert_not_called()

    def test_AI_update_configuration_rejects_empty_string_target(self, users, mocker):
        """Empty-string target_user_id must NOT be silently coerced to self.

        Previously the service used ``target_user_id or self._user_id`` which
        would falsy-coerce an empty string to the acting user and bypass the
        self-update guard. Now we require ``is None`` before defaulting.
        """
        mock = mocker.patch(
            "unique_toolkit.experimental.resources.user.functions.User.update_user_configuration"
        )

        with pytest.raises(ValueError, match="target_user_id must equal user_id"):
            users.update_configuration(
                configuration={"theme": "dark"}, target_user_id=""
            )

        mock.assert_not_called()

    def test_AI_update_configuration_accepts_self_target(self, users, mocker):
        """Explicitly passing the acting user's own id is allowed."""
        mock = mocker.patch(
            "unique_toolkit.experimental.resources.user.functions.User.update_user_configuration",
            return_value={
                **_user_payload(id=USER_ID),
                "userConfiguration": {"theme": "light"},
            },
        )

        user = users.update_configuration(
            configuration={"theme": "light"}, target_user_id=USER_ID
        )

        assert user.user_configuration == {"theme": "light"}
        mock.assert_called_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            userConfiguration={"theme": "light"},
        )

    @pytest.mark.asyncio
    async def test_AI_update_configuration_async_rejects_other_target(
        self, users, mocker
    ):
        """Async variant enforces the same self-update invariant."""
        mock = mocker.patch(
            "unique_toolkit.experimental.resources.user.functions.User.update_user_configuration_async"
        )

        with pytest.raises(ValueError, match="target_user_id must equal user_id"):
            await users.update_configuration_async(
                configuration={"theme": "dark"}, target_user_id="someone-else"
            )

        mock.assert_not_called()


# ── Groups ────────────────────────────────────────────────────────────────────


class TestAIGroupsList:
    def test_AI_list_forwards_name_filter(self, groups, mocker):
        """groups.list should forward the name filter to the SDK."""
        mock = mocker.patch(
            "unique_toolkit.experimental.resources.group.functions.Group.get_groups",
            return_value={"groups": [_group_payload()]},
        )

        result = groups.list(name="engineers")

        assert len(result) == 1
        assert isinstance(result[0], GroupInfo)
        mock.assert_called_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            skip=0,
            take=100,
            name="engineers",
        )


class TestAIGroupsCreate:
    def test_AI_create_minimum_params_sends_only_name(self, groups, mocker):
        """Optional parent_id / external_id must not appear when omitted."""
        mock = mocker.patch(
            "unique_toolkit.experimental.resources.group.functions.Group.create_group",
            return_value=_group_payload(name="new-team"),
        )

        group = groups.create(name="new-team")

        assert group.name == "new-team"
        mock.assert_called_once_with(
            user_id=USER_ID, company_id=COMPANY_ID, name="new-team"
        )

    def test_AI_create_with_parent_forwards_camel_case(self, groups, mocker):
        """parent_id/external_id must be serialised to camelCase on the wire."""
        mock = mocker.patch(
            "unique_toolkit.experimental.resources.group.functions.Group.create_group",
            return_value=_group_payload(
                id="g-2", name="sub-team", parentId="g-1", externalId="ext-2"
            ),
        )

        group = groups.create(name="sub-team", parent_id="g-1", external_id="ext-2")

        assert group.parent_id == "g-1"
        assert group.external_id == "ext-2"
        mock.assert_called_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            name="sub-team",
            parentId="g-1",
            externalId="ext-2",
        )


class TestAIGroupsDelete:
    def test_AI_delete_returns_group_deleted(self, groups, mocker):
        """groups.delete returns GroupDeleted with the deleted id."""
        mock = mocker.patch(
            "unique_toolkit.experimental.resources.group.functions.Group.delete_group",
            return_value={"id": "g-1"},
        )

        result = groups.delete("g-1")

        assert isinstance(result, GroupDeleted)
        assert result.id == "g-1"
        mock.assert_called_once_with(
            user_id=USER_ID, company_id=COMPANY_ID, group_id="g-1"
        )


class TestAIGroupsRename:
    def test_AI_rename_calls_update_with_new_name(self, groups, mocker):
        """groups.rename maps to SDK update_group(name=new_name)."""
        mock = mocker.patch(
            "unique_toolkit.experimental.resources.group.functions.Group.update_group",
            return_value=_group_payload(name="renamed"),
        )

        group = groups.rename("g-1", new_name="renamed")

        assert group.name == "renamed"
        mock.assert_called_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            group_id="g-1",
            name="renamed",
        )


class TestAIGroupsMembership:
    def test_AI_add_members_returns_membership_list(self, groups, mocker):
        """groups.add_members returns GroupMembership models for each new row."""
        mock = mocker.patch(
            "unique_toolkit.experimental.resources.group.functions.Group.add_users_to_group",
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

        memberships = groups.add_members("g-1", user_ids=["u-1", "u-2"])

        assert len(memberships) == 2
        assert all(isinstance(m, GroupMembership) for m in memberships)
        mock.assert_called_once_with(
            user_id=USER_ID,
            company_id=COMPANY_ID,
            group_id="g-1",
            userIds=["u-1", "u-2"],
        )

    def test_AI_add_members_with_empty_list_raises(self, groups, mocker):
        """Empty user_ids must be rejected client-side to avoid a no-op API call."""
        mocker.patch(
            "unique_toolkit.experimental.resources.group.functions.Group.add_users_to_group"
        )

        with pytest.raises(ValueError, match="must not be empty"):
            groups.add_members("g-1", user_ids=[])

    def test_AI_remove_members_returns_success_bool(self, groups, mocker):
        """groups.remove_members returns the raw success flag from the API."""
        mocker.patch(
            "unique_toolkit.experimental.resources.group.functions.Group.remove_users_from_group",
            return_value={"success": True},
        )

        assert groups.remove_members("g-1", user_ids=["u-1"]) is True

    @pytest.mark.asyncio
    async def test_AI_remove_members_async_delegates_to_async_sdk(self, groups, mocker):
        """Async variant must call the async SDK method."""
        mock = mocker.patch(
            "unique_toolkit.experimental.resources.group.functions.Group.remove_users_from_group_async",
            return_value={"success": False},
        )

        result = await groups.remove_members_async("g-1", user_ids=["u-1"])

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
        """Identity must reject None user/company ids (validate_required_values)."""
        with pytest.raises(ValueError, match="Required values cannot be None"):
            Identity(user_id=None, company_id=COMPANY_ID)  # type: ignore[arg-type]

    def test_AI_from_settings_uses_explicit_settings(self, mocker):
        """Passing a UniqueSettings forwards its confidential ids verbatim."""
        settings = mocker.Mock()
        settings.authcontext.get_confidential_company_id.return_value = "c-42"
        settings.authcontext.get_confidential_user_id.return_value = "u-42"

        identity = Identity.from_settings(settings)

        assert identity._company_id == "c-42"
        assert identity._user_id == "u-42"
        assert identity.users._user_id == "u-42"
        assert identity.groups._company_id == "c-42"

    def test_AI_from_settings_none_triggers_auto_init(self, mocker):
        """No-arg call must auto-load via UniqueSettings.from_env_auto_with_sdk_init."""
        settings = mocker.Mock()
        settings.authcontext.get_confidential_company_id.return_value = "c-env"
        settings.authcontext.get_confidential_user_id.return_value = "u-env"
        auto = mocker.patch(
            "unique_toolkit.app.unique_settings.UniqueSettings.from_env_auto_with_sdk_init",
            return_value=settings,
        )

        identity = Identity.from_settings()

        auto.assert_called_once_with()
        assert identity._company_id == "c-env"
        assert identity._user_id == "u-env"

    def test_AI_from_settings_string_forwards_filename(self, mocker):
        """Passing a string routes through from_env_auto_with_sdk_init(filename=...)."""
        settings = mocker.Mock()
        settings.authcontext.get_confidential_company_id.return_value = "c-file"
        settings.authcontext.get_confidential_user_id.return_value = "u-file"
        auto = mocker.patch(
            "unique_toolkit.app.unique_settings.UniqueSettings.from_env_auto_with_sdk_init",
            return_value=settings,
        )

        Identity.from_settings("my.env")

        auto.assert_called_once_with(filename="my.env")
