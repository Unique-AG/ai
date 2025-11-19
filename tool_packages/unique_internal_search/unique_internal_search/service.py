from logging import Logger

from pydantic import Field, create_model
from typing_extensions import override
from unique_toolkit._common.chunk_relevancy_sorter.exception import (
    ChunkRelevancySorterException,
)
from unique_toolkit._common.chunk_relevancy_sorter.service import ChunkRelevancySorter
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.history_manager.utils import transform_chunks_to_string
from unique_toolkit.agentic.tools.agent_chunks_hanlder import AgentChunksHandler
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.agentic.tools.tool_progress_reporter import ProgressState
from unique_toolkit.app.schemas import BaseEvent, ChatEvent, Event
from unique_toolkit.chat.schemas import (
    MessageLogDetails,
    MessageLogEvent,
)
from unique_toolkit.chat.service import LanguageModelToolDescription
from unique_toolkit.content.schemas import Content, ContentChunk, ContentReference
from unique_toolkit.content.service import ContentService
from unique_toolkit.content.utils import (
    merge_content_chunks,
    pick_content_chunks_for_token_window,
    sort_content_chunks,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelMessage,
    LanguageModelToolMessage,
)

from unique_internal_search.config import InternalSearchConfig
from unique_internal_search.utils import (
    SearchStringResult,
    append_metadata_in_chunks,
    clean_search_string,
    interleave_search_results_round_robin,
)


class InternalSearchService:
    def __init__(
        self,
        config: InternalSearchConfig,
        content_service: ContentService,
        chunk_relevancy_sorter: ChunkRelevancySorter,
        chat_id: str | None,
        logger: Logger,
    ):
        self.config = config
        self.content_service = content_service
        self.chunk_relevancy_sorter = chunk_relevancy_sorter
        self.chat_id = chat_id
        self.logger = logger
        self.tool_execution_message_name = "Internal search"

    async def post_progress_message(self, message: str, *args, **kwargs):
        pass

    async def get_uploaded_files(self) -> list[Content]:
        chat_results = await self.content_service.search_contents_async(
            where={
                "ownerId": {
                    "equals": self.chat_id,
                }
            },
        )
        sorted_chat_results: list[Content] = sorted(
            chat_results,
            key=lambda x: x.created_at,  # type: ignore
            reverse=True,
        )
        return sorted_chat_results

    async def is_chat_only(self, **kwargs) -> bool:
        """Check whether the assistant should limit itself to files in chat"""
        if self.config.chat_only:
            return True
        if self.config.scope_to_chat_on_upload:
            chat_files = await self.get_uploaded_files()
            if len(chat_files) > 0:
                return True
        return False

    async def search(
        self,
        search_string: str | list[str],
        content_ids: list[str] | None = None,
        metadata_filter: dict | None = None,
        **kwargs,
    ) -> list[ContentChunk]:
        """
        Perform a search with one or more search strings.

        Args:
            search_string: List of search strings or single search string
            content_ids: List of content IDs
            metadata_filter: Metadata filter
        """

        # Convert single string to list
        if isinstance(search_string, str):
            search_strings = [search_string]
        else:
            search_strings = search_string

        """
        Perform a search in the Vector DB based on the user's message and generate a response.
        """

        # Clean search strings by removing QDF and boost operators
        search_strings = [clean_search_string(s) for s in search_strings]

        ###
        # 2. Search for context in the Vector DB
        ###
        chat_only = await self.is_chat_only(**kwargs)

        """
        Handle the fact that metadata can exclude uploaded content
        and that the search service is hardcoded to use the metadata_filter 
        from the event if set to None
        """
        # Take a backup of the metadata filter
        metadata_filter_copy = self.content_service._metadata_filter

        if metadata_filter is None:
            metadata_filter = self.content_service._metadata_filter
        if chat_only and metadata_filter:
            # if this is not set to none search_content_chunks_async will overwrite it inside its call thats why it needs to stay.
            self.content_service._metadata_filter = None
            metadata_filter = None

        found_chunks_per_search_string: list[SearchStringResult] = []
        for i, search_string in enumerate(search_strings):
            try:
                found_chunks: list[
                    ContentChunk
                ] = await self.content_service.search_content_chunks_async(
                    search_string=search_string,  # type: ignore
                    search_type=self.config.search_type,
                    limit=self.config.limit,
                    reranker_config=self.config.reranker_config,
                    search_language=self.config.search_language,
                    scope_ids=self.config.scope_ids,
                    metadata_filter=metadata_filter,
                    chat_id=self.chat_id
                    if not self.config.exclude_uploaded_files and self.chat_id
                    else "NO_CHAT",  # deliberate string to avoid if chat_id condition.
                    chat_only=chat_only,
                    content_ids=content_ids,
                    score_threshold=self.config.score_threshold,
                )
                self.logger.info(
                    f"Found {len(found_chunks)} chunks (Query {i + 1}/{len(search_strings)})"
                )
            except Exception as e:
                self.logger.error(f"Error in search_document_chunks call: {e}")
                raise e

            found_chunks_per_search_string.append(
                SearchStringResult(
                    query=search_string,
                    chunks=found_chunks,
                )
            )

        # Updating our logger with the search results for all search strings.

        # Reset the metadata filter in case it was disabled
        self.content_service._metadata_filter = metadata_filter_copy

        # Apply chunk relevancy sorter if enabled
        if self.config.chunk_relevancy_sort_config.enabled:
            for i, result in enumerate(found_chunks_per_search_string):
                await self.post_progress_message(
                    f"{result.query} (_Resorting {len(result.chunks)} search results_ 🔄 in query {i + 1}/{len(search_strings)})",
                    **kwargs,
                )
                result.chunks = await self._resort_found_chunks_if_enabled(
                    found_chunks=result.chunks,
                    search_string=result.query,
                )

        ###
        # 3. Pick a subset of the search results
        ###
        if (
            self.config.experimental_features.enable_multiple_search_strings_execution
            and len(found_chunks_per_search_string) > 1
        ):
            found_chunks_per_search_string = interleave_search_results_round_robin(
                found_chunks_per_search_string
            )

        await self.post_progress_message(
            f"{', '.join(search_strings)} (_Postprocessing search results_)",
            **kwargs,
        )
        found_chunks = [
            chunk
            for result in found_chunks_per_search_string
            for chunk in result.chunks
        ]
        selected_chunks = pick_content_chunks_for_token_window(
            found_chunks, self._get_max_tokens()
        )

        ###
        # 4. cache them add index to search results & join them together
        ###
        if not self.config.chunked_sources:
            selected_chunks = merge_content_chunks(selected_chunks)
        else:
            selected_chunks = sort_content_chunks(selected_chunks)

        self.debug_info = {
            "searchStrings": search_strings,
            "metadataFilter": metadata_filter,
            "chatOnly": chat_only,
        }
        return selected_chunks

    async def _resort_found_chunks_if_enabled(
        self, found_chunks: list[ContentChunk], search_string: str
    ) -> list[ContentChunk]:
        try:
            total_chunks = len(found_chunks)
            self.logger.info(f"Resorting {total_chunks} search result...")
            chunk_relevancy_sorter_result = await self.chunk_relevancy_sorter.run(
                input_text=search_string,
                chunks=found_chunks,
                config=self.config.chunk_relevancy_sort_config,
            )
            found_chunks = chunk_relevancy_sorter_result.content_chunks
        except ChunkRelevancySorterException as e:
            self.logger.warning(f"Error while sorting chunks: {e.error_message}")
        finally:
            return found_chunks

    def _get_max_tokens(self) -> int:
        if self.config.language_model_max_input_tokens is not None:
            max_tokens = int(
                self.config.language_model_max_input_tokens
                * self.config.percentage_of_input_tokens_for_sources
            )
            self.logger.debug(
                "Using %s of max tokens %s as token limit: %s",
                self.config.percentage_of_input_tokens_for_sources,
                self.config.language_model_max_input_tokens,
                max_tokens,
            )
            return max_tokens
        else:
            self.logger.debug(
                "language model input context size is not set, using default max tokens"
            )
            return self.config.max_tokens_for_sources


class InternalSearchTool(Tool[InternalSearchConfig], InternalSearchService):
    name = "InternalSearch"

    def __init__(
        self,
        configuration: InternalSearchConfig,
        event: BaseEvent,
        *args,
        **kwargs,
    ):
        Tool.__init__(self, configuration, event, *args, **kwargs)

        content_service = ContentService.from_event(self.event)
        chunk_relevancy_sorter = ChunkRelevancySorter.from_event(self.event)
        # Determing chat_id if possible
        if isinstance(self.event, (ChatEvent, Event)):
            chat_id = self.event.payload.chat_id
        else:
            chat_id = None
        InternalSearchService.__init__(
            self,
            config=configuration,
            content_service=content_service,
            chunk_relevancy_sorter=chunk_relevancy_sorter,
            chat_id=chat_id,
            logger=self.logger,
        )

    async def post_progress_message(
        self, message: str, tool_call: LanguageModelFunction, **kwargs
    ):
        if self.tool_progress_reporter:
            await self.tool_progress_reporter.notify_from_tool_call(
                tool_call=tool_call,
                name=f"**{self.tool_execution_message_name}**",
                message=message,
                state=ProgressState.RUNNING,
            )

    async def is_chat_only(
        self, tool_call: LanguageModelFunction | None = None, **kwargs
    ) -> bool:
        if await super().is_chat_only(**kwargs):
            return True
        if (
            tool_call
            and isinstance(tool_call.arguments, dict)
            and tool_call.arguments.get("chat_only") is True
        ):
            return True
        return False

    @override
    def tool_description(self) -> LanguageModelToolDescription:
        # Conditionally set the type based on config
        search_string_type = (
            list[str]
            if self.config.experimental_features.enable_multiple_search_strings_execution
            else str
        )

        internal_search_tool_input = create_model(
            "InternalSearchToolInput",
            search_string=(
                search_string_type,
                Field(description=self.config.param_description_search_string),
            ),
            language=(
                str,
                Field(description=self.config.param_description_language),
            ),
        )
        return LanguageModelToolDescription(
            name=self.name,
            description=self.config.tool_description,
            parameters=internal_search_tool_input,
        )

    def tool_description_for_system_prompt(self) -> str:
        return self.config.tool_description_for_system_prompt

    def tool_format_information_for_system_prompt(self) -> str:
        return self.config.tool_format_information_for_system_prompt

    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return self.config.evaluation_check_list

    def get_evaluation_checks_based_on_tool_response(
        self, tool_response: ToolCallResponse
    ) -> list[EvaluationMetricName]:
        evaluation_check_list = self.evaluation_check_list()

        # Check if the tool response is empty
        if not tool_response.content_chunks:
            return []
        return evaluation_check_list

    # TODO: find a solution for tracking
    # @track(name="internal_search_tool_run")
    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        """
        Perform a search in the Vector DB based on the user's message and generate a response.
        """
        if (
            tool_call.arguments is None
            or not isinstance(tool_call.arguments, dict)
            or (
                "search_strings" not in tool_call.arguments
                and "search_string"
                not in tool_call.arguments  # Backwards compatibility
            )
        ):
            self.logger.error("Tool call arguments are missing or invalid")
            return ToolCallResponse(
                id=tool_call.id,  # type: ignore
                name=self.name,
                content_chunks=[],
                debug_info={},
            )

        # Extract the search strings (handle both new and old parameter names)
        search_strings_data = tool_call.arguments.get(
            "search_strings", tool_call.arguments.get("search_string")
        )
        # Ensure it's always a list for the progress message
        search_strings_list: list[str] = []
        if isinstance(search_strings_data, str):
            search_strings_list = [search_strings_data]
        elif isinstance(search_strings_data, list):
            search_strings_list = search_strings_data
        else:
            raise ValueError("Invalid search strings data")

        await self.post_progress_message(f"{'; '.join(search_strings_list)}", tool_call)

        selected_chunks = await self.search(
            **tool_call.arguments,
            tool_call=tool_call,  # Need to pass tool_call to post_progress_message
        )

        ## Message log entry
        await self._create_message_log_entry(
            chunks=selected_chunks, search_strings_list=search_strings_list
        )

        ## Modify metadata in chunks
        selected_chunks = append_metadata_in_chunks(
            chunks=selected_chunks,
            metadata_chunk_sections=self.config.metadata_chunk_sections,
        )

        tool_response = ToolCallResponse(
            id=tool_call.id,  # type: ignore
            name=self.name,
            content_chunks=selected_chunks,
            debug_info=self.debug_info,
        )

        if self.tool_progress_reporter:
            await self.tool_progress_reporter.notify_from_tool_call(
                tool_call=tool_call,
                name=f"**{self.tool_execution_message_name}**",
                message=f"{'; '.join(search_strings_list)}",
                state=ProgressState.FINISHED,
            )

        return tool_response

    async def _create_message_log_entry(
        self, *, chunks: list[ContentChunk], search_strings_list: list[str]
    ) -> None:
        message_log_reference_list: list[
            ContentReference
        ] = await self._define_reference_list_for_message_log(
            content_chunks=chunks,
        )
        details = await self._prepare_message_log_details(
            query_list=search_strings_list
        )
        self._message_step_logger.create_message_log_entry(
            text="**Internal Search**",
            details=details,
            data=message_log_reference_list,
        )

    async def _define_reference_list_for_message_log(
        self,
        *,
        content_chunks: list[ContentChunk],
    ) -> list[ContentReference]:
        """
        Create a reference list for internal search content chunks.

        Args:
            content_chunks: List of ContentChunk objects to convert
        Returns:
            List of ContentReference objects
        """
        data: list[ContentReference] = []
        count = 0
        for content_chunk in content_chunks:
            reference_name: str = content_chunk.title or content_chunk.key or ""

            if reference_name != "":
                data.append(
                    ContentReference(
                        name=reference_name,
                        sequence_number=count,
                        source="internal",
                        url="",
                        source_id=content_chunk.id,
                    )
                )
                count += 1

        return data

    async def _prepare_message_log_details(
        self, *, query_list: list[str]
    ) -> MessageLogDetails:
        details = MessageLogDetails(
            data=[
                MessageLogEvent(
                    type="InternalSearch",
                    text=query_for_log,
                )
                for query_for_log in query_list
            ]
        )

        return details

    ## Note: This function is only used by the Investment Research Agent and Agentic Search. Once these agents are moved out of the monorepo, this function should be removed.
    def get_tool_call_result_for_loop_history(
        self,
        tool_response: ToolCallResponse,
        agent_chunks_handler: AgentChunksHandler,
    ) -> LanguageModelMessage:
        """
        Process the results of the tool.
        Args:
            tool_response: The tool response.
            loop_history: The loop history.
        Returns:
            The tool result to append to the loop history.
        """
        self.logger.debug(
            f"Appending tool call result to history: {tool_response.name}"
        )
        # Initialize content_chunks if None
        content_chunks = tool_response.content_chunks or []

        # Get the maximum source number in the loop history
        max_source_number = len(agent_chunks_handler.chunks)

        # Transform content chunks into sources to be appended to tool result
        sources, _ = transform_chunks_to_string(
            content_chunks,
            max_source_number,
        )

        # Append the result to the history
        return LanguageModelToolMessage(
            content=sources,
            tool_call_id=tool_response.id,  # type: ignore
            name=tool_response.name,
        )


ToolFactory.register_tool(InternalSearchTool, InternalSearchConfig)
