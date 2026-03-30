"""Unit tests for ChatService.from_settings."""

import pytest
from pydantic import SecretStr

from unique_toolkit.app.unique_settings import (
    AuthContext,
    ChatContext,
    UniqueContext,
)
from unique_toolkit.chat.cancellation import CancellationWatcher
from unique_toolkit.services.chat_service import ChatService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def auth() -> AuthContext:
    return AuthContext(user_id=SecretStr("user-1"), company_id=SecretStr("company-1"))


@pytest.fixture
def chat() -> ChatContext:
    return ChatContext(
        chat_id="chat-1",
        assistant_id="assistant-1",
        last_assistant_message_id="amsg-1",
        last_user_message_id="umsg-1",
        last_user_message_text="",
    )


@pytest.fixture
def context(auth: AuthContext, chat: ChatContext) -> UniqueContext:
    return UniqueContext(auth=auth, chat=chat)


@pytest.fixture
def auth_only_context(auth: AuthContext) -> UniqueContext:
    return UniqueContext(auth=auth)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestChatServiceFromContext:
    @pytest.mark.ai
    def test_from_context__returns_chat_service_instance(
        self, context: UniqueContext
    ) -> None:
        """
        Purpose: Verify that from_settings returns a ChatService instance.
        Why this matters: Callers depend on receiving the correct type to access chat methods.
        Setup summary: Full context; assert isinstance check.
        """
        svc = ChatService.from_context(context)
        assert isinstance(svc, ChatService)

    @pytest.mark.ai
    def test_from_context__sets_company_id__from_auth(
        self, context: UniqueContext
    ) -> None:
        """
        Purpose: Verify _company_id is extracted from the auth context.
        Why this matters: Wrong company_id would route API calls to the wrong tenant.
        Setup summary: Auth with company-1; assert _company_id == "company-1".
        """
        svc = ChatService.from_context(context)
        assert svc._company_id == "company-1"

    @pytest.mark.ai
    def test_from_context__sets_user_id__from_auth(
        self, context: UniqueContext
    ) -> None:
        """
        Purpose: Verify _user_id is extracted from the auth context.
        Why this matters: Wrong user_id would attribute messages to the wrong user.
        Setup summary: Auth with user-1; assert _user_id == "user-1".
        """
        svc = ChatService.from_context(context)
        assert svc._user_id == "user-1"

    @pytest.mark.ai
    def test_from_context__sets_chat_id__from_chat_context(
        self, context: UniqueContext
    ) -> None:
        """
        Purpose: Verify _chat_id is taken from the chat context.
        Why this matters: All message operations are scoped to the chat_id.
        Setup summary: Chat with chat_id="chat-1"; assert _chat_id matches.
        """
        svc = ChatService.from_context(context)
        assert svc._chat_id == "chat-1"

    @pytest.mark.ai
    def test_from_context__sets_assistant_id__from_chat_context(
        self, context: UniqueContext
    ) -> None:
        """
        Purpose: Verify _assistant_id is taken from the chat context.
        Why this matters: Incorrect assistant_id silently sends replies to the wrong assistant.
        Setup summary: Chat with assistant_id="assistant-1"; assert _assistant_id matches.
        """
        svc = ChatService.from_context(context)
        assert svc._assistant_id == "assistant-1"

    @pytest.mark.ai
    def test_from_context__sets_assistant_message_id__from_last_assistant_message_id(
        self, context: UniqueContext
    ) -> None:
        """
        Purpose: Verify _assistant_message_id maps to last_assistant_message_id.
        Why this matters: Message edits use this id; a wrong value corrupts the reply thread.
        Setup summary: Chat with last_assistant_message_id="amsg-1"; assert _assistant_message_id matches.
        """
        svc = ChatService.from_context(context)
        assert svc._assistant_message_id == "amsg-1"

    @pytest.mark.ai
    def test_from_context__sets_user_message_id__from_chat_context(
        self, context: UniqueContext
    ) -> None:
        """
        Purpose: Verify _user_message_id is taken from the chat context.
        Why this matters: Needed to retrieve and update the triggering user message.
        Setup summary: Chat with last_user_message_id="umsg-1"; assert _user_message_id matches.
        """
        svc = ChatService.from_context(context)
        assert svc._user_message_id == "umsg-1"

    @pytest.mark.ai
    def test_from_context__sets_user_message_text__to_empty_string(
        self, context: UniqueContext
    ) -> None:
        """
        Purpose: Verify _user_message_text is initialised to an empty string.
        Why this matters: Context-based construction has no event to pull text from; callers must not see stale data.
        Setup summary: Full context; assert _user_message_text == "".
        """
        svc = ChatService.from_context(context)
        assert svc._user_message_text == ""

    @pytest.mark.ai
    def test_from_context__event_is_none(self, context: UniqueContext) -> None:
        """
        Purpose: Verify _event is None when constructed from a context (not an event).
        Why this matters: The deprecated event property must not leak a stale event object.
        Setup summary: Full context; assert _event is None.
        """
        svc = ChatService.from_context(context)
        assert svc._event is None

    @pytest.mark.ai
    def test_from_context__cancellation_watcher_is_initialized(
        self, context: UniqueContext
    ) -> None:
        """
        Purpose: Verify the CancellationWatcher is set up by from_settings.
        Why this matters: Missing watcher means cancellation checks silently do nothing.
        Setup summary: Full context; assert _cancellation_watcher is a CancellationWatcher.
        """
        svc = ChatService.from_context(context)
        assert isinstance(svc._cancellation_watcher, CancellationWatcher)

    @pytest.mark.ai
    def test_from_context__content_scope_falls_back_to_chat_id__when_no_parent(
        self, context: UniqueContext
    ) -> None:
        """
        Purpose: Verify _content_scope_chat_id defaults to chat_id when parent_chat_id is absent.
        Why this matters: Content search must still work in a non-subagent scenario.
        Setup summary: Chat with no parent_chat_id; assert _content_scope_chat_id == chat_id.
        """
        svc = ChatService.from_context(context)
        assert svc._content_scope_chat_id == "chat-1"

    @pytest.mark.ai
    def test_from_context__content_scope_uses_parent_chat_id__when_set(
        self, auth: AuthContext
    ) -> None:
        """
        Purpose: Verify _content_scope_chat_id is set to parent_chat_id in subagent scenarios.
        Why this matters: Subagents must search the parent session's uploaded files, not their own.
        Setup summary: Chat with parent_chat_id="parent-99"; assert _content_scope_chat_id == "parent-99".
        """
        chat_with_parent = ChatContext(
            chat_id="chat-1",
            assistant_id="assistant-1",
            last_assistant_message_id="amsg-1",
            last_user_message_id="umsg-1",
            last_user_message_text="",
            parent_chat_id="parent-99",
        )
        svc = ChatService.from_context(UniqueContext(auth=auth, chat=chat_with_parent))
        assert svc._content_scope_chat_id == "parent-99"

    @pytest.mark.ai
    def test_from_context__raises_value_error__when_chat_is_none(
        self, auth_only_context: UniqueContext
    ) -> None:
        """
        Purpose: Verify a clear ValueError is raised when no chat context is provided.
        Why this matters: ChatService cannot function without chat ids; a silent failure would be hard to debug.
        Setup summary: Auth-only context (chat=None); assert ValueError.
        """
        with pytest.raises(ValueError, match="context.chat is None"):
            ChatService.from_context(auth_only_context)

    @pytest.mark.ai
    def test_from_context__raises_value_error__when_user_message_id_is_none(
        self, auth: AuthContext
    ) -> None:
        """
        Purpose: Verify a clear ValueError is raised when last_user_message_id is missing.
        Why this matters: Without a user_message_id the service cannot reference the triggering message.
        Setup summary: Chat without last_user_message_id set; assert ValueError.
        """
        chat_no_user_msg = ChatContext(
            chat_id="chat-1",
            assistant_id="assistant-1",
            last_assistant_message_id="amsg-1",
        )
        with pytest.raises(ValueError):
            ChatService.from_context(UniqueContext(auth=auth, chat=chat_no_user_msg))
