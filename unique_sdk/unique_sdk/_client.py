from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unique_sdk._http_client import HTTPClient


class _BaseClient:
    """Shared configuration for sync and async clients."""

    api_key: str | None
    app_id: str | None
    api_base: str
    api_version: str
    additional_headers: dict[str, str]
    _http_client: HTTPClient | None

    def __init__(
        self,
        *,
        api_key: str | None = None,
        app_id: str | None = None,
        api_base: str | None = None,
        api_version: str | None = None,
        additional_headers: dict[str, str] | None = None,
        http_client: HTTPClient | None = None,
    ) -> None:
        import unique_sdk

        self.api_key = api_key if api_key is not None else unique_sdk.api_key
        self.app_id = app_id if app_id is not None else unique_sdk.app_id
        self.api_base = api_base if api_base is not None else unique_sdk.api_base
        self.api_version = (
            api_version if api_version is not None else unique_sdk.api_version
        )
        self.additional_headers = dict(additional_headers) if additional_headers else {}
        self._http_client = http_client


class UniqueClient(_BaseClient):
    """Synchronous SDK client.

    Initialise once with your credentials and optional extra headers, then
    call any resource through the typed accessor properties::

        client = UniqueClient(
            api_key="ukey_...",
            app_id="app_...",
            additional_headers={"x-trace-id": "abc123"},
        )
        results = client.search.create(user_id, company_id, searchString="...")
    """

    @property
    def acronyms(self) -> _SyncAcronymsAccessor:
        return _SyncAcronymsAccessor(self)

    @property
    def analytics_order(self) -> _SyncAnalyticsOrderAccessor:
        return _SyncAnalyticsOrderAccessor(self)

    @property
    def benchmarking(self) -> _SyncBenchmarkingAccessor:
        return _SyncBenchmarkingAccessor(self)

    @property
    def briefing(self) -> _SyncBriefingAccessor:
        return _SyncBriefingAccessor(self)

    @property
    def chat_completion(self) -> _SyncChatCompletionAccessor:
        return _SyncChatCompletionAccessor(self)

    @property
    def content(self) -> _SyncContentAccessor:
        return _SyncContentAccessor(self)

    @property
    def dynamic_frontend(self) -> _SyncDynamicFrontendAccessor:
        return _SyncDynamicFrontendAccessor(self)

    @property
    def elicitation(self) -> _SyncElicitationAccessor:
        return _SyncElicitationAccessor(self)

    @property
    def embeddings(self) -> _SyncEmbeddingsAccessor:
        return _SyncEmbeddingsAccessor(self)

    @property
    def folder(self) -> _SyncFolderAccessor:
        return _SyncFolderAccessor(self)

    @property
    def group(self) -> _SyncGroupAccessor:
        return _SyncGroupAccessor(self)

    @property
    def integrated(self) -> _SyncIntegratedAccessor:
        return _SyncIntegratedAccessor(self)

    @property
    def llm_models(self) -> _SyncLLMModelsAccessor:
        return _SyncLLMModelsAccessor(self)

    @property
    def mcp(self) -> _SyncMCPAccessor:
        return _SyncMCPAccessor(self)

    @property
    def message(self) -> _SyncMessageAccessor:
        return _SyncMessageAccessor(self)

    @property
    def message_assessment(self) -> _SyncMessageAssessmentAccessor:
        return _SyncMessageAssessmentAccessor(self)

    @property
    def message_execution(self) -> _SyncMessageExecutionAccessor:
        return _SyncMessageExecutionAccessor(self)

    @property
    def message_log(self) -> _SyncMessageLogAccessor:
        return _SyncMessageLogAccessor(self)

    @property
    def message_tool(self) -> _SyncMessageToolAccessor:
        return _SyncMessageToolAccessor(self)

    @property
    def module(self) -> _SyncModuleAccessor:
        return _SyncModuleAccessor(self)

    @property
    def scheduled_task(self) -> _SyncScheduledTaskAccessor:
        return _SyncScheduledTaskAccessor(self)

    @property
    def search(self) -> _SyncSearchAccessor:
        return _SyncSearchAccessor(self)

    @property
    def search_string(self) -> _SyncSearchStringAccessor:
        return _SyncSearchStringAccessor(self)

    @property
    def short_term_memory(self) -> _SyncShortTermMemoryAccessor:
        return _SyncShortTermMemoryAccessor(self)

    @property
    def space(self) -> _SyncSpaceAccessor:
        return _SyncSpaceAccessor(self)

    @property
    def user(self) -> _SyncUserAccessor:
        return _SyncUserAccessor(self)

    @property
    def web_search(self) -> _SyncWebSearchAccessor:
        return _SyncWebSearchAccessor(self)

    @property
    def web_crawl(self) -> _SyncWebCrawlAccessor:
        return _SyncWebCrawlAccessor(self)


class AsyncUniqueClient(_BaseClient):
    """Asynchronous SDK client.

    Initialise once with your credentials and optional extra headers, then
    await any resource through the typed accessor properties::

        client = AsyncUniqueClient(
            api_key="ukey_...",
            app_id="app_...",
            additional_headers={"x-trace-id": "abc123"},
        )
        results = await client.search.create(user_id, company_id, searchString="...")
    """

    @property
    def acronyms(self) -> _AsyncAcronymsAccessor:
        return _AsyncAcronymsAccessor(self)

    @property
    def agentic_table(self) -> _AsyncAgenticTableAccessor:
        return _AsyncAgenticTableAccessor(self)

    @property
    def analytics_order(self) -> _AsyncAnalyticsOrderAccessor:
        return _AsyncAnalyticsOrderAccessor(self)

    @property
    def benchmarking(self) -> _AsyncBenchmarkingAccessor:
        return _AsyncBenchmarkingAccessor(self)

    @property
    def briefing(self) -> _AsyncBriefingAccessor:
        return _AsyncBriefingAccessor(self)

    @property
    def chat_completion(self) -> _AsyncChatCompletionAccessor:
        return _AsyncChatCompletionAccessor(self)

    @property
    def content(self) -> _AsyncContentAccessor:
        return _AsyncContentAccessor(self)

    @property
    def elicitation(self) -> _AsyncElicitationAccessor:
        return _AsyncElicitationAccessor(self)

    @property
    def embeddings(self) -> _AsyncEmbeddingsAccessor:
        return _AsyncEmbeddingsAccessor(self)

    @property
    def folder(self) -> _AsyncFolderAccessor:
        return _AsyncFolderAccessor(self)

    @property
    def group(self) -> _AsyncGroupAccessor:
        return _AsyncGroupAccessor(self)

    @property
    def integrated(self) -> _AsyncIntegratedAccessor:
        return _AsyncIntegratedAccessor(self)

    @property
    def llm_models(self) -> _AsyncLLMModelsAccessor:
        return _AsyncLLMModelsAccessor(self)

    @property
    def mcp(self) -> _AsyncMCPAccessor:
        return _AsyncMCPAccessor(self)

    @property
    def message(self) -> _AsyncMessageAccessor:
        return _AsyncMessageAccessor(self)

    @property
    def message_assessment(self) -> _AsyncMessageAssessmentAccessor:
        return _AsyncMessageAssessmentAccessor(self)

    @property
    def message_execution(self) -> _AsyncMessageExecutionAccessor:
        return _AsyncMessageExecutionAccessor(self)

    @property
    def message_log(self) -> _AsyncMessageLogAccessor:
        return _AsyncMessageLogAccessor(self)

    @property
    def message_tool(self) -> _AsyncMessageToolAccessor:
        return _AsyncMessageToolAccessor(self)

    @property
    def module(self) -> _AsyncModuleAccessor:
        return _AsyncModuleAccessor(self)

    @property
    def scheduled_task(self) -> _AsyncScheduledTaskAccessor:
        return _AsyncScheduledTaskAccessor(self)

    @property
    def search(self) -> _AsyncSearchAccessor:
        return _AsyncSearchAccessor(self)

    @property
    def search_string(self) -> _AsyncSearchStringAccessor:
        return _AsyncSearchStringAccessor(self)

    @property
    def short_term_memory(self) -> _AsyncShortTermMemoryAccessor:
        return _AsyncShortTermMemoryAccessor(self)

    @property
    def space(self) -> _AsyncSpaceAccessor:
        return _AsyncSpaceAccessor(self)

    @property
    def user(self) -> _AsyncUserAccessor:
        return _AsyncUserAccessor(self)

    @property
    def web_search(self) -> _AsyncWebSearchAccessor:
        return _AsyncWebSearchAccessor(self)

    @property
    def web_crawl(self) -> _AsyncWebCrawlAccessor:
        return _AsyncWebCrawlAccessor(self)


# ---------------------------------------------------------------------------
# Sync accessor classes — forward to the *non*-async resource classmethods.
# ---------------------------------------------------------------------------


class _SyncAcronymsAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def get(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._acronyms import Acronyms

        return Acronyms.get(user_id, company_id, client=self._client, **params)


class _SyncAnalyticsOrderAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._analytics_order import AnalyticsOrder

        return AnalyticsOrder.create(user_id, company_id, client=self._client, **params)

    def list(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._analytics_order import AnalyticsOrder

        return AnalyticsOrder.list(user_id, company_id, client=self._client, **params)

    def retrieve(self, user_id: str, company_id: str, order_id: str):
        from unique_sdk.api_resources._analytics_order import AnalyticsOrder

        return AnalyticsOrder.retrieve(
            user_id, company_id, order_id, client=self._client
        )

    def delete(self, user_id: str, company_id: str, order_id: str):
        from unique_sdk.api_resources._analytics_order import AnalyticsOrder

        return AnalyticsOrder.delete(user_id, company_id, order_id, client=self._client)

    def download(self, user_id: str, company_id: str, order_id: str):
        from unique_sdk.api_resources._analytics_order import AnalyticsOrder

        return AnalyticsOrder.download(
            user_id, company_id, order_id, client=self._client
        )


class _SyncBenchmarkingAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def process_upload(
        self,
        user_id: str,
        company_id: str,
        file: bytes,
        filename: str,
        force: bool | None = None,
    ):
        from unique_sdk.api_resources._benchmarking import Benchmarking

        return Benchmarking.process_upload(
            user_id, company_id, file, filename, force, client=self._client
        )

    def get_status(self, user_id: str, company_id: str):
        from unique_sdk.api_resources._benchmarking import Benchmarking

        return Benchmarking.get_status(user_id, company_id, client=self._client)

    def download_processed(self, user_id: str, company_id: str):
        from unique_sdk.api_resources._benchmarking import Benchmarking

        return Benchmarking.download_processed(user_id, company_id, client=self._client)

    def download_template(self, user_id: str, company_id: str):
        from unique_sdk.api_resources._benchmarking import Benchmarking

        return Benchmarking.download_template(user_id, company_id, client=self._client)


class _SyncBriefingAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def upsert_for_assistant(
        self, *, user_id: str, company_id: str, assistant_id: str, **params
    ):
        from unique_sdk.api_resources._briefing import Briefing

        return Briefing.upsert_for_assistant(
            user_id=user_id,
            company_id=company_id,
            assistant_id=assistant_id,
            client=self._client,
            **params,
        )


class _SyncChatCompletionAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._chat_completion import ChatCompletion

        return ChatCompletion.create(user_id, company_id, client=self._client, **params)


class _SyncContentAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def search(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._content import Content

        return Content.search(user_id, company_id, client=self._client, **params)

    def get_info(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._content import Content

        return Content.get_info(user_id, company_id, client=self._client, **params)

    def get_infos(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._content import Content

        return Content.get_infos(user_id, company_id, client=self._client, **params)

    def upsert(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._content import Content

        return Content.upsert(user_id, company_id, client=self._client, **params)

    def versions(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._content import Content

        return Content.versions(user_id, company_id, client=self._client, **params)

    def version_download_url(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._content import Content

        return Content.version_download_url(
            user_id, company_id, client=self._client, **params
        )

    def restore_version(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._content import Content

        return Content.restore_version(
            user_id, company_id, client=self._client, **params
        )

    def ingest_magic_table_sheets(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._content import Content

        return Content.ingest_magic_table_sheets(
            user_id, company_id, client=self._client, **params
        )

    def update(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._content import Content

        return Content.update(user_id, company_id, client=self._client, **params)

    def update_ingestion_state(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._content import Content

        return Content.update_ingestion_state(
            user_id, company_id, client=self._client, **params
        )

    def delete(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._content import Content

        return Content.delete(user_id, company_id, client=self._client, **params)

    def resolve_content_id_from_file_path(
        self, user_id: str, company_id: str, **params
    ):
        from unique_sdk.api_resources._content import Content

        return Content.resolve_content_id_from_file_path(
            user_id, company_id, client=self._client, **params
        )


class _SyncDynamicFrontendAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._dynamic_frontend import DynamicFrontend

        return DynamicFrontend.create(
            user_id, company_id, client=self._client, **params
        )

    def modify(self, space_id: str, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._dynamic_frontend import DynamicFrontend

        return DynamicFrontend.modify(
            space_id, user_id, company_id, client=self._client, **params
        )

    def delete(self, space_id: str, user_id: str, company_id: str):
        from unique_sdk.api_resources._dynamic_frontend import DynamicFrontend

        return DynamicFrontend.delete(
            space_id, user_id, company_id, client=self._client
        )

    def list(self, user_id: str, company_id: str):
        from unique_sdk.api_resources._dynamic_frontend import DynamicFrontend

        return DynamicFrontend.list(user_id, company_id, client=self._client)


class _SyncElicitationAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def create_elicitation(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._elicitation import Elicitation

        return Elicitation.create_elicitation(
            user_id, company_id, client=self._client, **params
        )

    def get_pending_elicitations(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._elicitation import Elicitation

        return Elicitation.get_pending_elicitations(
            user_id, company_id, client=self._client, **params
        )

    def get_elicitation(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._elicitation import Elicitation

        return Elicitation.get_elicitation(
            user_id, company_id, client=self._client, **params
        )

    def respond_to_elicitation(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._elicitation import Elicitation

        return Elicitation.respond_to_elicitation(
            user_id, company_id, client=self._client, **params
        )


class _SyncEmbeddingsAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._embedding import Embeddings

        return Embeddings.create(user_id, company_id, client=self._client, **params)


class _SyncFolderAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def get_folder_path(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._folder import Folder

        return Folder.get_folder_path(
            user_id, company_id, client=self._client, **params
        )

    def get_info(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._folder import Folder

        return Folder.get_info(user_id, company_id, client=self._client, **params)

    def get_infos(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._folder import Folder

        return Folder.get_infos(user_id, company_id, client=self._client, **params)

    def create_paths(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._folder import Folder

        return Folder.create_paths(user_id, company_id, client=self._client, **params)

    def update_ingestion_config(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._folder import Folder

        return Folder.update_ingestion_config(
            user_id, company_id, client=self._client, **params
        )

    def add_access(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._folder import Folder

        return Folder.add_access(user_id, company_id, client=self._client, **params)

    def remove_access(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._folder import Folder

        return Folder.remove_access(user_id, company_id, client=self._client, **params)

    def update(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._folder import Folder

        return Folder.update(user_id, company_id, client=self._client, **params)

    def move(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._folder import Folder

        return Folder.move(user_id, company_id, client=self._client, **params)

    def delete(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._folder import Folder

        return Folder.delete(user_id, company_id, client=self._client, **params)

    def resolve_scope_id_from_folder_path(
        self, user_id: str, company_id: str, **params
    ):
        from unique_sdk.api_resources._folder import Folder

        return Folder.resolve_scope_id_from_folder_path(
            user_id, company_id, client=self._client, **params
        )

    def resolve_scope_id_from_folder_path_with_create(
        self, user_id: str, company_id: str, **params
    ):
        from unique_sdk.api_resources._folder import Folder

        return Folder.resolve_scope_id_from_folder_path_with_create(
            user_id, company_id, client=self._client, **params
        )


class _SyncGroupAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def create_group(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._group import Group

        return Group.create_group(user_id, company_id, client=self._client, **params)

    def get_groups(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._group import Group

        return Group.get_groups(user_id, company_id, client=self._client, **params)

    def delete_group(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._group import Group

        return Group.delete_group(user_id, company_id, client=self._client, **params)

    def update_group(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._group import Group

        return Group.update_group(user_id, company_id, client=self._client, **params)

    def add_users_to_group(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._group import Group

        return Group.add_users_to_group(
            user_id, company_id, client=self._client, **params
        )

    def remove_users_from_group(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._group import Group

        return Group.remove_users_from_group(
            user_id, company_id, client=self._client, **params
        )

    def update_group_configuration(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._group import Group

        return Group.update_group_configuration(
            user_id, company_id, client=self._client, **params
        )


class _SyncIntegratedAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def chat_stream_completion(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._integrated import Integrated

        return Integrated.chat_stream_completion(
            user_id, company_id, client=self._client, **params
        )


class _SyncLLMModelsAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def get_models(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._llm_models import LLMModels

        return LLMModels.get_models(user_id, company_id, client=self._client, **params)


class _SyncMCPAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def call_tool(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._mcp import MCP

        return MCP.call_tool(user_id, company_id, client=self._client, **params)


class _SyncMessageAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def list(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message import Message

        return Message.list(user_id, company_id, client=self._client, **params)

    def retrieve(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message import Message

        return Message.retrieve(user_id, company_id, client=self._client, **params)

    def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message import Message

        return Message.create(user_id, company_id, client=self._client, **params)

    def modify(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message import Message

        return Message.modify(user_id, company_id, client=self._client, **params)


class _SyncMessageAssessmentAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message_assessment import MessageAssessment

        return MessageAssessment.create(
            user_id, company_id, client=self._client, **params
        )

    def modify(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message_assessment import MessageAssessment

        return MessageAssessment.modify(
            user_id, company_id, client=self._client, **params
        )


class _SyncMessageExecutionAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message_execution import MessageExecution

        return MessageExecution.create(
            user_id, company_id, client=self._client, **params
        )

    def get(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message_execution import MessageExecution

        return MessageExecution.get(user_id, company_id, client=self._client, **params)

    def update(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message_execution import MessageExecution

        return MessageExecution.update(
            user_id, company_id, client=self._client, **params
        )


class _SyncMessageLogAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message_log import MessageLog

        return MessageLog.create(user_id, company_id, client=self._client, **params)

    def update(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message_log import MessageLog

        return MessageLog.update(user_id, company_id, client=self._client, **params)


class _SyncMessageToolAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def create_many(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message_tool import MessageTool

        return MessageTool.create_many(
            user_id, company_id, client=self._client, **params
        )

    def get_message_tools(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message_tool import MessageTool

        return MessageTool.get_message_tools(
            user_id, company_id, client=self._client, **params
        )


class _SyncModuleAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def list(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._module import Module

        return Module.list(
            user_id=user_id, company_id=company_id, client=self._client, **params
        )

    def retrieve(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._module import Module

        return Module.retrieve(
            user_id=user_id, company_id=company_id, client=self._client, **params
        )

    def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._module import Module

        return Module.create(
            user_id=user_id, company_id=company_id, client=self._client, **params
        )

    def modify(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._module import Module

        return Module.modify(
            user_id=user_id, company_id=company_id, client=self._client, **params
        )

    def delete(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._module import Module

        return Module.delete(
            user_id=user_id, company_id=company_id, client=self._client, **params
        )


class _SyncScheduledTaskAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._scheduled_task import ScheduledTask

        return ScheduledTask.create(user_id, company_id, client=self._client, **params)

    def list(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._scheduled_task import ScheduledTask

        return ScheduledTask.list(user_id, company_id, client=self._client, **params)

    def retrieve(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._scheduled_task import ScheduledTask

        return ScheduledTask.retrieve(
            user_id, company_id, client=self._client, **params
        )

    def modify(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._scheduled_task import ScheduledTask

        return ScheduledTask.modify(user_id, company_id, client=self._client, **params)

    def delete(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._scheduled_task import ScheduledTask

        return ScheduledTask.delete(user_id, company_id, client=self._client, **params)


class _SyncSearchAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._search import Search

        return Search.create(user_id, company_id, client=self._client, **params)


class _SyncSearchStringAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._search_string import SearchString

        return SearchString.create(user_id, company_id, client=self._client, **params)


class _SyncShortTermMemoryAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._short_term_memory import ShortTermMemory

        return ShortTermMemory.create(
            user_id, company_id, client=self._client, **params
        )

    def find_latest(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._short_term_memory import ShortTermMemory

        return ShortTermMemory.find_latest(
            user_id, company_id, client=self._client, **params
        )


class _SyncSpaceAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def create_message(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return Space.create_message(user_id, company_id, client=self._client, **params)

    def create_chat(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return Space.create_chat(user_id, company_id, client=self._client, **params)

    def get_chat_messages(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return Space.get_chat_messages(
            user_id, company_id, client=self._client, **params
        )

    def get_latest_message(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return Space.get_latest_message(
            user_id, company_id, client=self._client, **params
        )

    def delete_chat(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return Space.delete_chat(user_id, company_id, client=self._client, **params)

    def get_space(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return Space.get_space(user_id, company_id, client=self._client, **params)

    def create_space(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return Space.create_space(user_id, company_id, client=self._client, **params)

    def get_space_access(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return Space.get_space_access(
            user_id, company_id, client=self._client, **params
        )

    def add_space_access(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return Space.add_space_access(
            user_id, company_id, client=self._client, **params
        )

    def delete_space_access(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return Space.delete_space_access(
            user_id, company_id, client=self._client, **params
        )

    def update_space(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return Space.update_space(user_id, company_id, client=self._client, **params)

    def delete_space(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return Space.delete_space(user_id, company_id, client=self._client, **params)

    def get_spaces(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return Space.get_spaces(user_id, company_id, client=self._client, **params)


class _SyncUserAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def get_users(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._user import User

        return User.get_users(user_id, company_id, client=self._client, **params)

    def update_user_configuration(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._user import User

        return User.update_user_configuration(
            user_id, company_id, client=self._client, **params
        )

    def get_by_id(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._user import User

        return User.get_by_id(user_id, company_id, client=self._client, **params)

    def get_user_groups(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._user import User

        return User.get_user_groups(user_id, company_id, client=self._client, **params)


class _SyncWebSearchAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def search(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._web_search import WebSearch

        return WebSearch.search(user_id, company_id, client=self._client, **params)


class _SyncWebCrawlAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: UniqueClient) -> None:
        self._client = client

    def crawl(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._web_search import WebCrawl

        return WebCrawl.crawl(user_id, company_id, client=self._client, **params)


# ---------------------------------------------------------------------------
# Async accessor classes — forward to the *_async resource classmethods,
# using the same base method name (no _async suffix from the caller's POV).
# ---------------------------------------------------------------------------


class _AsyncAcronymsAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def get(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._acronyms import Acronyms

        return await Acronyms.get_async(
            user_id, company_id, client=self._client, **params
        )


class _AsyncAgenticTableAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def set_cell(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._agentic_table import AgenticTable

        return await AgenticTable.set_cell(
            user_id, company_id, client=self._client, **params
        )

    async def get_cell(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._agentic_table import AgenticTable

        return await AgenticTable.get_cell(
            user_id, company_id, client=self._client, **params
        )

    async def set_activity(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._agentic_table import AgenticTable

        return await AgenticTable.set_activity(
            user_id, company_id, client=self._client, **params
        )

    async def set_artifact(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._agentic_table import AgenticTable

        return await AgenticTable.set_artifact(
            user_id, company_id, client=self._client, **params
        )

    async def update_sheet_state(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._agentic_table import AgenticTable

        return await AgenticTable.update_sheet_state(
            user_id, company_id, client=self._client, **params
        )

    async def set_column_metadata(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._agentic_table import AgenticTable

        return await AgenticTable.set_column_metadata(
            user_id, company_id, client=self._client, **params
        )

    async def get_sheet_data(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._agentic_table import AgenticTable

        return await AgenticTable.get_sheet_data(
            user_id, company_id, client=self._client, **params
        )

    async def get_sheet_state(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._agentic_table import AgenticTable

        return await AgenticTable.get_sheet_state(
            user_id, company_id, client=self._client, **params
        )

    async def set_cell_metadata(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._agentic_table import AgenticTable

        return await AgenticTable.set_cell_metadata(
            user_id, company_id, client=self._client, **params
        )

    async def set_multiple_cells(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._agentic_table import AgenticTable

        return await AgenticTable.set_multiple_cells(
            user_id, company_id, client=self._client, **params
        )

    async def bulk_update_status(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._agentic_table import AgenticTable

        return await AgenticTable.bulk_update_status(
            user_id, company_id, client=self._client, **params
        )


class _AsyncAnalyticsOrderAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._analytics_order import AnalyticsOrder

        return await AnalyticsOrder.create_async(
            user_id, company_id, client=self._client, **params
        )

    async def list(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._analytics_order import AnalyticsOrder

        return await AnalyticsOrder.list_async(
            user_id, company_id, client=self._client, **params
        )

    async def retrieve(self, user_id: str, company_id: str, order_id: str):
        from unique_sdk.api_resources._analytics_order import AnalyticsOrder

        return await AnalyticsOrder.retrieve_async(
            user_id, company_id, order_id, client=self._client
        )

    async def delete(self, user_id: str, company_id: str, order_id: str):
        from unique_sdk.api_resources._analytics_order import AnalyticsOrder

        return await AnalyticsOrder.delete_async(
            user_id, company_id, order_id, client=self._client
        )

    async def download(self, user_id: str, company_id: str, order_id: str):
        from unique_sdk.api_resources._analytics_order import AnalyticsOrder

        return await AnalyticsOrder.download_async(
            user_id, company_id, order_id, client=self._client
        )


class _AsyncBenchmarkingAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def process_upload(
        self,
        user_id: str,
        company_id: str,
        file: bytes,
        filename: str,
        force: bool | None = None,
    ):
        from unique_sdk.api_resources._benchmarking import Benchmarking

        return await Benchmarking.process_upload_async(
            user_id, company_id, file, filename, force, client=self._client
        )

    async def get_status(self, user_id: str, company_id: str):
        from unique_sdk.api_resources._benchmarking import Benchmarking

        return await Benchmarking.get_status_async(
            user_id, company_id, client=self._client
        )

    async def download_processed(self, user_id: str, company_id: str):
        from unique_sdk.api_resources._benchmarking import Benchmarking

        return await Benchmarking.download_processed_async(
            user_id, company_id, client=self._client
        )

    async def download_template(self, user_id: str, company_id: str):
        from unique_sdk.api_resources._benchmarking import Benchmarking

        return await Benchmarking.download_template_async(
            user_id, company_id, client=self._client
        )


class _AsyncBriefingAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def upsert_for_assistant(
        self, *, user_id: str, company_id: str, assistant_id: str, **params
    ):
        from unique_sdk.api_resources._briefing import Briefing

        return await Briefing.upsert_for_assistant_async(
            user_id=user_id,
            company_id=company_id,
            assistant_id=assistant_id,
            client=self._client,
            **params,
        )


class _AsyncChatCompletionAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._chat_completion import ChatCompletion

        return await ChatCompletion.create_async(
            user_id, company_id, client=self._client, **params
        )


class _AsyncContentAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def search(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._content import Content

        return await Content.search_async(
            user_id, company_id, client=self._client, **params
        )

    async def get_info(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._content import Content

        return await Content.get_info_async(
            user_id, company_id, client=self._client, **params
        )

    async def get_infos(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._content import Content

        return await Content.get_infos_async(
            user_id, company_id, client=self._client, **params
        )

    async def upsert(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._content import Content

        return await Content.upsert_async(
            user_id, company_id, client=self._client, **params
        )

    async def versions(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._content import Content

        return await Content.versions_async(
            user_id, company_id, client=self._client, **params
        )

    async def version_download_url(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._content import Content

        return await Content.version_download_url_async(
            user_id, company_id, client=self._client, **params
        )

    async def restore_version(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._content import Content

        return await Content.restore_version_async(
            user_id, company_id, client=self._client, **params
        )

    async def ingest_magic_table_sheets(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._content import Content

        return await Content.ingest_magic_table_sheets_async(
            user_id, company_id, client=self._client, **params
        )

    async def update(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._content import Content

        return await Content.update_async(
            user_id, company_id, client=self._client, **params
        )

    async def update_ingestion_state(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._content import Content

        return await Content.update_ingestion_state_async(
            user_id, company_id, client=self._client, **params
        )

    async def delete(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._content import Content

        return await Content.delete_async(
            user_id, company_id, client=self._client, **params
        )

    async def resolve_content_id_from_file_path(
        self, user_id: str, company_id: str, **params
    ):
        from unique_sdk.api_resources._content import Content

        return Content.resolve_content_id_from_file_path(
            user_id, company_id, client=self._client, **params
        )


class _AsyncElicitationAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def create_elicitation(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._elicitation import Elicitation

        return await Elicitation.create_elicitation_async(
            user_id, company_id, client=self._client, **params
        )

    async def get_pending_elicitations(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._elicitation import Elicitation

        return await Elicitation.get_pending_elicitations_async(
            user_id, company_id, client=self._client, **params
        )

    async def get_elicitation(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._elicitation import Elicitation

        return await Elicitation.get_elicitation_async(
            user_id, company_id, client=self._client, **params
        )

    async def respond_to_elicitation(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._elicitation import Elicitation

        return await Elicitation.respond_to_elicitation_async(
            user_id, company_id, client=self._client, **params
        )


class _AsyncEmbeddingsAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._embedding import Embeddings

        return await Embeddings.create_async(
            user_id, company_id, client=self._client, **params
        )


class _AsyncFolderAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def get_folder_path(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._folder import Folder

        return await Folder.get_folder_path_async(
            user_id, company_id, client=self._client, **params
        )

    async def get_info(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._folder import Folder

        return await Folder.get_info_async(
            user_id, company_id, client=self._client, **params
        )

    async def get_infos(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._folder import Folder

        return await Folder.get_infos_async(
            user_id, company_id, client=self._client, **params
        )

    async def create_paths(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._folder import Folder

        return await Folder.create_paths_async(
            user_id, company_id, client=self._client, **params
        )

    async def update_ingestion_config(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._folder import Folder

        return await Folder.update_ingestion_config_async(
            user_id, company_id, client=self._client, **params
        )

    async def add_access(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._folder import Folder

        return await Folder.add_access_async(
            user_id, company_id, client=self._client, **params
        )

    async def remove_access(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._folder import Folder

        return await Folder.remove_access_async(
            user_id, company_id, client=self._client, **params
        )

    async def update(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._folder import Folder

        return await Folder.update_async(
            user_id, company_id, client=self._client, **params
        )

    async def move(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._folder import Folder

        return await Folder.move_async(
            user_id, company_id, client=self._client, **params
        )

    async def delete(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._folder import Folder

        return await Folder.delete_async(
            user_id, company_id, client=self._client, **params
        )

    async def resolve_scope_id_from_folder_path(
        self, user_id: str, company_id: str, **params
    ):
        from unique_sdk.api_resources._folder import Folder

        return await Folder.resolve_scope_id_from_folder_path_async(
            user_id, company_id, client=self._client, **params
        )

    async def resolve_scope_id_from_folder_path_with_create(
        self, user_id: str, company_id: str, **params
    ):
        from unique_sdk.api_resources._folder import Folder

        return await Folder.resolve_scope_id_from_folder_path_with_create_async(
            user_id, company_id, client=self._client, **params
        )


class _AsyncGroupAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def create_group(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._group import Group

        return await Group.create_group_async(
            user_id, company_id, client=self._client, **params
        )

    async def get_groups(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._group import Group

        return await Group.get_groups_async(
            user_id, company_id, client=self._client, **params
        )

    async def delete_group(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._group import Group

        return await Group.delete_group_async(
            user_id, company_id, client=self._client, **params
        )

    async def update_group(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._group import Group

        return await Group.update_group_async(
            user_id, company_id, client=self._client, **params
        )

    async def add_users_to_group(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._group import Group

        return await Group.add_users_to_group_async(
            user_id, company_id, client=self._client, **params
        )

    async def remove_users_from_group(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._group import Group

        return await Group.remove_users_from_group_async(
            user_id, company_id, client=self._client, **params
        )

    async def update_group_configuration(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._group import Group

        return await Group.update_group_configuration_async(
            user_id, company_id, client=self._client, **params
        )


class _AsyncIntegratedAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def chat_stream_completion(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._integrated import Integrated

        return await Integrated.chat_stream_completion_async(
            user_id, company_id, client=self._client, **params
        )


class _AsyncLLMModelsAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def get_models(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._llm_models import LLMModels

        return await LLMModels.get_models_async(
            user_id, company_id, client=self._client, **params
        )


class _AsyncMCPAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def call_tool(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._mcp import MCP

        return await MCP.call_tool_async(
            user_id, company_id, client=self._client, **params
        )


class _AsyncMessageAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def list(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message import Message

        return await Message.list_async(
            user_id, company_id, client=self._client, **params
        )

    async def retrieve(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message import Message

        return await Message.retrieve_async(
            user_id, company_id, client=self._client, **params
        )

    async def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message import Message

        return await Message.create_async(
            user_id, company_id, client=self._client, **params
        )

    async def modify(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message import Message

        return await Message.modify_async(
            user_id, company_id, client=self._client, **params
        )


class _AsyncMessageAssessmentAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message_assessment import MessageAssessment

        return await MessageAssessment.create_async(
            user_id, company_id, client=self._client, **params
        )

    async def modify(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message_assessment import MessageAssessment

        return await MessageAssessment.modify_async(
            user_id, company_id, client=self._client, **params
        )


class _AsyncMessageExecutionAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message_execution import MessageExecution

        return await MessageExecution.create_async(
            user_id, company_id, client=self._client, **params
        )

    async def get(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message_execution import MessageExecution

        return await MessageExecution.get_async(
            user_id, company_id, client=self._client, **params
        )

    async def update(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message_execution import MessageExecution

        return await MessageExecution.update_async(
            user_id, company_id, client=self._client, **params
        )


class _AsyncMessageLogAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message_log import MessageLog

        return await MessageLog.create_async(
            user_id, company_id, client=self._client, **params
        )

    async def update(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message_log import MessageLog

        return await MessageLog.update_async(
            user_id, company_id, client=self._client, **params
        )


class _AsyncMessageToolAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def create_many(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message_tool import MessageTool

        return await MessageTool.create_many_async(
            user_id, company_id, client=self._client, **params
        )

    async def get_message_tools(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._message_tool import MessageTool

        return await MessageTool.get_message_tools_async(
            user_id, company_id, client=self._client, **params
        )


class _AsyncModuleAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def list(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._module import Module

        return await Module.list_async(
            user_id=user_id, company_id=company_id, client=self._client, **params
        )

    async def retrieve(self, user_id: str, company_id: str, id: str, **params):
        from unique_sdk.api_resources._module import Module

        return await Module.retrieve_async(
            user_id=user_id, company_id=company_id, id=id, client=self._client
        )

    async def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._module import Module

        return await Module.create_async(
            user_id=user_id, company_id=company_id, client=self._client, **params
        )

    async def modify(self, user_id: str, company_id: str, id: str, **params):
        from unique_sdk.api_resources._module import Module

        return await Module.modify_async(
            user_id=user_id, company_id=company_id, id=id, client=self._client, **params
        )

    async def delete(self, user_id: str, company_id: str, id: str, **params):
        from unique_sdk.api_resources._module import Module

        return await Module.delete_async(
            user_id=user_id, company_id=company_id, id=id, client=self._client
        )


class _AsyncScheduledTaskAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._scheduled_task import ScheduledTask

        return await ScheduledTask.create_async(
            user_id, company_id, client=self._client, **params
        )

    async def list(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._scheduled_task import ScheduledTask

        return await ScheduledTask.list_async(
            user_id, company_id, client=self._client, **params
        )

    async def retrieve(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._scheduled_task import ScheduledTask

        return await ScheduledTask.retrieve_async(
            user_id, company_id, client=self._client, **params
        )

    async def modify(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._scheduled_task import ScheduledTask

        return await ScheduledTask.modify_async(
            user_id, company_id, client=self._client, **params
        )

    async def delete(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._scheduled_task import ScheduledTask

        return await ScheduledTask.delete_async(
            user_id, company_id, client=self._client, **params
        )


class _AsyncSearchAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._search import Search

        return await Search.create_async(
            user_id, company_id, client=self._client, **params
        )


class _AsyncSearchStringAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._search_string import SearchString

        return await SearchString.create_async(
            user_id, company_id, client=self._client, **params
        )


class _AsyncShortTermMemoryAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def create(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._short_term_memory import ShortTermMemory

        return await ShortTermMemory.create_async(
            user_id, company_id, client=self._client, **params
        )

    async def find_latest(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._short_term_memory import ShortTermMemory

        return await ShortTermMemory.find_latest_async(
            user_id, company_id, client=self._client, **params
        )


class _AsyncSpaceAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def create_message(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return await Space.create_message_async(
            user_id, company_id, client=self._client, **params
        )

    async def create_chat(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return await Space.create_chat_async(
            user_id, company_id, client=self._client, **params
        )

    async def get_chat_messages(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return await Space.get_chat_messages_async(
            user_id, company_id, client=self._client, **params
        )

    async def get_latest_message(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return await Space.get_latest_message_async(
            user_id, company_id, client=self._client, **params
        )

    async def delete_chat(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return await Space.delete_chat_async(
            user_id, company_id, client=self._client, **params
        )

    async def get_space(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return await Space.get_space_async(
            user_id, company_id, client=self._client, **params
        )

    async def create_space(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return await Space.create_space_async(
            user_id, company_id, client=self._client, **params
        )

    async def get_space_access(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return await Space.get_space_access_async(
            user_id, company_id, client=self._client, **params
        )

    async def add_space_access(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return await Space.add_space_access_async(
            user_id, company_id, client=self._client, **params
        )

    async def delete_space_access(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return await Space.delete_space_access_async(
            user_id, company_id, client=self._client, **params
        )

    async def update_space(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return await Space.update_space_async(
            user_id, company_id, client=self._client, **params
        )

    async def delete_space(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return await Space.delete_space_async(
            user_id, company_id, client=self._client, **params
        )

    async def get_spaces(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._space import Space

        return await Space.get_spaces_async(
            user_id, company_id, client=self._client, **params
        )


class _AsyncUserAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def get_users(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._user import User

        return await User.get_users_async(
            user_id, company_id, client=self._client, **params
        )

    async def update_user_configuration(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._user import User

        return await User.update_user_configuration_async(
            user_id, company_id, client=self._client, **params
        )

    async def get_by_id(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._user import User

        return await User.get_by_id_async(
            user_id, company_id, client=self._client, **params
        )

    async def get_user_groups(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._user import User

        return await User.get_user_groups_async(
            user_id, company_id, client=self._client, **params
        )


class _AsyncWebSearchAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def search(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._web_search import WebSearch

        return await WebSearch.search_async(
            user_id, company_id, client=self._client, **params
        )


class _AsyncWebCrawlAccessor:
    __slots__ = ("_client",)

    def __init__(self, client: AsyncUniqueClient) -> None:
        self._client = client

    async def crawl(self, user_id: str, company_id: str, **params):
        from unique_sdk.api_resources._web_search import WebCrawl

        return await WebCrawl.crawl_async(
            user_id, company_id, client=self._client, **params
        )
