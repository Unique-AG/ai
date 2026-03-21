"""UniqueClient — the top-level entry point for the Unique SDK OOP layer."""

from __future__ import annotations

import unique_sdk

from .resources._agentic_table import AgenticTableManager
from .resources._completion import ChatCompletionManager, IntegratedManager
from .resources._content import (
    ContentManager,
    EmbeddingsManager,
    SearchManager,
    SearchStringManager,
)
from .resources._elicitation import ElicitationManager
from .resources._folder import FolderManager
from .resources._group import GroupManager
from .resources._memory import MemoryManager
from .resources._message import (
    MessageAssessmentManager,
    MessageExecutionManager,
    MessageLogManager,
    MessageManager,
    MessageToolManager,
)
from .resources._misc import AcronymsManager, MCPManager, ModelsManager
from .resources._space import SpaceManager
from .resources._user import UserManager


class UniqueClient:
    """OOP entry point for the Unique SDK.

    Instantiate once with your credentials and interact with all API resources
    through typed manager objects — no need to pass ``user_id`` / ``company_id``
    on every call.

    Example::

        client = UniqueClient(
            user_id="usr_...",
            company_id="cmp_...",
            api_key="ukey_...",
            app_id="app_...",
        )

        # Create an assistant message
        msg = await client.messages.create(
            chatId="chat_123",
            assistantId="asst_456",
            role="ASSISTANT",
            text="Hello!",
            references=None,
            debugInfo=None,
            completedAt=None,
        )

        # Modify it in-place
        await msg.modify(text="Hello, world!")

        # Search knowledge base
        results = await client.content.search(
            chatId="chat_123",
            searchString="quarterly report",
            scopeIds=["scope_abc"],
            limit=10,
        )
        for item in results:
            print(item.id, item.key)
    """

    def __init__(
        self,
        user_id: str,
        company_id: str,
        api_key: str | None = None,
        app_id: str | None = None,
    ) -> None:
        self._user_id = user_id
        self._company_id = company_id

        if api_key is not None:
            unique_sdk.api_key = api_key
        if app_id is not None:
            unique_sdk.app_id = app_id

        # Lazy-initialised managers (None until first access)
        self._messages: MessageManager | None = None
        self._message_logs: MessageLogManager | None = None
        self._message_tools: MessageToolManager | None = None
        self._message_assessments: MessageAssessmentManager | None = None
        self._message_executions: MessageExecutionManager | None = None
        self._content: ContentManager | None = None
        self._search: SearchManager | None = None
        self._search_strings: SearchStringManager | None = None
        self._embeddings: EmbeddingsManager | None = None
        self._spaces: SpaceManager | None = None
        self._folders: FolderManager | None = None
        self._chat_completion: ChatCompletionManager | None = None
        self._integrated: IntegratedManager | None = None
        self._users: UserManager | None = None
        self._groups: GroupManager | None = None
        self._memory: MemoryManager | None = None
        self._elicitation: ElicitationManager | None = None
        self._agentic_table: AgenticTableManager | None = None
        self._models: ModelsManager | None = None
        self._acronyms: AcronymsManager | None = None
        self._mcp: MCPManager | None = None

    # ------------------------------------------------------------------
    # Message family
    # ------------------------------------------------------------------

    @property
    def messages(self) -> MessageManager:
        """CRUD operations for chat messages."""
        if self._messages is None:
            self._messages = MessageManager(self._user_id, self._company_id)
        return self._messages

    @property
    def message_logs(self) -> MessageLogManager:
        """Create and update message execution logs."""
        if self._message_logs is None:
            self._message_logs = MessageLogManager(self._user_id, self._company_id)
        return self._message_logs

    @property
    def message_tools(self) -> MessageToolManager:
        """Manage tool calls attached to messages."""
        if self._message_tools is None:
            self._message_tools = MessageToolManager(self._user_id, self._company_id)
        return self._message_tools

    @property
    def message_assessments(self) -> MessageAssessmentManager:
        """Create and update message quality assessments."""
        if self._message_assessments is None:
            self._message_assessments = MessageAssessmentManager(
                self._user_id, self._company_id
            )
        return self._message_assessments

    @property
    def message_executions(self) -> MessageExecutionManager:
        """Track long-running message executions (e.g. deep research)."""
        if self._message_executions is None:
            self._message_executions = MessageExecutionManager(
                self._user_id, self._company_id
            )
        return self._message_executions

    # ------------------------------------------------------------------
    # Content & search
    # ------------------------------------------------------------------

    @property
    def content(self) -> ContentManager:
        """Search, upsert and manage knowledge-base content."""
        if self._content is None:
            self._content = ContentManager(self._user_id, self._company_id)
        return self._content

    @property
    def search(self) -> SearchManager:
        """Vector similarity search over the knowledge base."""
        if self._search is None:
            self._search = SearchManager(self._user_id, self._company_id)
        return self._search

    @property
    def search_strings(self) -> SearchStringManager:
        """Generate optimised search queries from chat history."""
        if self._search_strings is None:
            self._search_strings = SearchStringManager(self._user_id, self._company_id)
        return self._search_strings

    @property
    def embeddings(self) -> EmbeddingsManager:
        """Generate text embeddings via the Unique gateway."""
        if self._embeddings is None:
            self._embeddings = EmbeddingsManager(self._user_id, self._company_id)
        return self._embeddings

    # ------------------------------------------------------------------
    # Spaces
    # ------------------------------------------------------------------

    @property
    def spaces(self) -> SpaceManager:
        """Create and manage Unique AI spaces."""
        if self._spaces is None:
            self._spaces = SpaceManager(self._user_id, self._company_id)
        return self._spaces

    # ------------------------------------------------------------------
    # Folders
    # ------------------------------------------------------------------

    @property
    def folders(self) -> FolderManager:
        """Create and manage knowledge-base folders."""
        if self._folders is None:
            self._folders = FolderManager(self._user_id, self._company_id)
        return self._folders

    # ------------------------------------------------------------------
    # LLM completions
    # ------------------------------------------------------------------

    @property
    def chat_completion(self) -> ChatCompletionManager:
        """OpenAI-compatible chat completions via the Unique gateway."""
        if self._chat_completion is None:
            self._chat_completion = ChatCompletionManager(
                self._user_id, self._company_id
            )
        return self._chat_completion

    @property
    def integrated(self) -> IntegratedManager:
        """Unique's native streaming LLM API with built-in search context."""
        if self._integrated is None:
            self._integrated = IntegratedManager(self._user_id, self._company_id)
        return self._integrated

    # ------------------------------------------------------------------
    # Users & groups
    # ------------------------------------------------------------------

    @property
    def users(self) -> UserManager:
        """Retrieve and manage platform users."""
        if self._users is None:
            self._users = UserManager(self._user_id, self._company_id)
        return self._users

    @property
    def groups(self) -> GroupManager:
        """Create and manage user groups."""
        if self._groups is None:
            self._groups = GroupManager(self._user_id, self._company_id)
        return self._groups

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------

    @property
    def memory(self) -> MemoryManager:
        """Short-term memory for chat sessions."""
        if self._memory is None:
            self._memory = MemoryManager(self._user_id, self._company_id)
        return self._memory

    # ------------------------------------------------------------------
    # Elicitation (human-in-the-loop)
    # ------------------------------------------------------------------

    @property
    def elicitation(self) -> ElicitationManager:
        """Create and respond to human-in-the-loop elicitation requests."""
        if self._elicitation is None:
            self._elicitation = ElicitationManager(self._user_id, self._company_id)
        return self._elicitation

    # ------------------------------------------------------------------
    # Agentic table
    # ------------------------------------------------------------------

    @property
    def agentic_table(self) -> AgenticTableManager:
        """AI-powered spreadsheet (agentic table) operations."""
        if self._agentic_table is None:
            self._agentic_table = AgenticTableManager(self._user_id, self._company_id)
        return self._agentic_table

    # ------------------------------------------------------------------
    # Miscellaneous
    # ------------------------------------------------------------------

    @property
    def models(self) -> ModelsManager:
        """List available LLM models."""
        if self._models is None:
            self._models = ModelsManager(self._user_id, self._company_id)
        return self._models

    @property
    def acronyms(self) -> AcronymsManager:
        """Retrieve company-specific acronyms."""
        if self._acronyms is None:
            self._acronyms = AcronymsManager(self._user_id, self._company_id)
        return self._acronyms

    @property
    def mcp(self) -> MCPManager:
        """Call tools registered via the Model Context Protocol."""
        if self._mcp is None:
            self._mcp = MCPManager(self._user_id, self._company_id)
        return self._mcp

    def __repr__(self) -> str:
        return (
            f"UniqueClient(user_id={self._user_id!r}, "
            f"company_id={self._company_id!r})"
        )
