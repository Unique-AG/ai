"""The ProjectChatSearch tool: search and read the earlier chats of a project."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import override

from pydantic import ValidationError
from unique_toolkit.agentic.evaluation.schemas import EvaluationMetricName
from unique_toolkit.agentic.tools.factory import ToolFactory
from unique_toolkit.agentic.tools.schemas import ToolCallResponse
from unique_toolkit.agentic.tools.tool import Tool
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.content.schemas import ContentChunk
from unique_toolkit.experimental.resources.project_chat import (
    ProjectChatChunkPage,
    ProjectChats,
    ProjectChatSummaryPage,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelFunction,
    LanguageModelToolDescription,
)

from unique_project_chat_search.config import ProjectChatSearchConfig
from unique_project_chat_search.schemas import ProjectChatSearchInput, parse_day
from unique_project_chat_search.sources import (
    excerpt_source,
    fit_to_budget,
    listing_source,
)

PROJECT_CHAT_SEARCH_TOOL_NAME = "ProjectChatSearch"

type _Fetch[PageT] = Callable[[str | None], Awaitable[PageT]]

USAGE = (
    'Call ProjectChatSearch with a `mode`: {"mode": "search", "query": "..."}, '
    '{"mode": "read", "chat_id": "chat_..."} or {"mode": "recent"}.'
)
UNKNOWN_CHAT = (
    "No chat with that chat_id in this project, or it has no messages yet. "
    "Use a chat_id from an earlier ProjectChatSearch result."
)
CURRENT_CHAT = (
    "That is the current chat; it is already in the conversation. "
    "ProjectChatSearch only covers the project's earlier chats."
)


class _Correction(Exception):
    """Arguments the model can fix; the message tells it how."""


class ProjectChatSearchTool(Tool[ProjectChatSearchConfig]):
    """Search and read the user's earlier chats in the current project.

    One input schema for every use (``mode`` = search, read or recent) and one
    output: the platform's standard sources, cited like internal or web search
    results. The orchestrator injects the tool only for project chats.
    """

    name = PROJECT_CHAT_SEARCH_TOOL_NAME
    default_display_name = "Project Chat Search"

    @override
    def display_name(self) -> str:
        return self.settings.display_name or self.default_display_name

    @override
    def tool_description(self) -> LanguageModelToolDescription:
        return LanguageModelToolDescription(
            name=self.name,
            description=self.config.tool_description,
            parameters=ProjectChatSearchInput,
        )

    @override
    def tool_description_for_system_prompt(self) -> str:
        return self.config.tool_description_for_system_prompt

    @override
    def evaluation_check_list(self) -> list[EvaluationMetricName]:
        return []

    @override
    def get_evaluation_checks_based_on_tool_response(
        self, tool_response: ToolCallResponse
    ) -> list[EvaluationMetricName]:
        return []

    # ── Run ───────────────────────────────────────────────────────────────

    @override
    async def run(self, tool_call: LanguageModelFunction) -> ToolCallResponse:
        call_id = tool_call.id or "unknown_id"
        event: ChatEvent | None = getattr(self, "_event", None)
        if event is None or not event.payload.project_id:
            return self._response(
                call_id, error_message="ProjectChatSearch only works in project chats."
            )
        try:
            arguments = ProjectChatSearchInput.model_validate(tool_call.arguments or {})
            return await self._dispatch(call_id, event, arguments)
        except ValidationError:
            return self._response(call_id, content=USAGE)
        except _Correction as correction:
            return self._response(call_id, content=str(correction))
        except Exception as error:
            if getattr(error, "http_status", None) == 404:
                return self._response(call_id, content=UNKNOWN_CHAT)
            self.logger.exception("ProjectChatSearch failed")
            return self._response(
                call_id, error_message="Could not search the project's earlier chats."
            )

    async def _dispatch(
        self, call_id: str, event: ChatEvent, arguments: ProjectChatSearchInput
    ) -> ToolCallResponse:
        project_chats = ProjectChats.from_event(event)
        current_chats = self._current_chat_ids(event)
        if arguments.chat_id in current_chats:
            raise _Correction(CURRENT_CHAT)

        if arguments.mode == "search":
            return await self._search(call_id, project_chats, current_chats, arguments)
        if arguments.mode == "read":
            return await self._read(call_id, project_chats, arguments)
        return await self._recent(call_id, project_chats, current_chats, arguments)

    async def _search(
        self,
        call_id: str,
        project_chats: ProjectChats,
        current_chats: list[str],
        arguments: ProjectChatSearchInput,
    ) -> ToolCallResponse:
        if not arguments.query:
            raise _Correction(
                'mode "search" needs a `query`, e.g. {"mode": "search", "query": "..."}.'
            )
        after, before = self._window(arguments)
        page = await project_chats.search_async(
            query=arguments.query,
            chat_ids=[arguments.chat_id] if arguments.chat_id else None,
            exclude_chat_ids=current_chats,
            created_after=after,
            created_before=before,
            limit=self.config.search_limit,
        )
        sources = [
            excerpt_source(chunk, url_template=self.config.chat_url_template)
            for chunk in page.chunks
        ]
        return self._sources_response(call_id, sources, next_page=None)

    async def _read(
        self,
        call_id: str,
        project_chats: ProjectChats,
        arguments: ProjectChatSearchInput,
    ) -> ToolCallResponse:
        chat_id = arguments.chat_id
        if not chat_id:
            raise _Correction(
                'mode "read" needs a `chat_id` from an earlier result, '
                'e.g. {"mode": "read", "chat_id": "chat_..."}.'
            )
        self._check_page(arguments.page)

        async def fetch(cursor: str | None) -> ProjectChatChunkPage:
            return await project_chats.list_chunks_async(
                chat_id=chat_id, limit=self.config.chunks_per_page, after=cursor
            )

        page, has_more = await self._walk_to_page(fetch, arguments.page)
        if arguments.page == 1 and (page is None or not page.chunks):
            # The endpoint answers an unknown chat id with an empty page.
            raise _Correction(UNKNOWN_CHAT)
        sources = [
            excerpt_source(chunk, url_template=self.config.chat_url_template)
            for chunk in (page.chunks if page else [])
        ]
        return self._sources_response(
            call_id, sources, next_page=arguments.page + 1 if has_more else None
        )

    async def _recent(
        self,
        call_id: str,
        project_chats: ProjectChats,
        current_chats: list[str],
        arguments: ProjectChatSearchInput,
    ) -> ToolCallResponse:
        self._check_page(arguments.page)
        after, before = self._window(arguments)

        async def fetch(cursor: str | None) -> ProjectChatSummaryPage:
            return await project_chats.list_recent_async(
                exclude_chat_ids=current_chats,
                updated_after=after,
                updated_before=before,
                limit=self.config.recent_limit,
                after=cursor,
            )

        page, has_more = await self._walk_to_page(fetch, arguments.page)
        offset = (arguments.page - 1) * self.config.recent_limit
        sources = [
            listing_source(
                chat,
                position=offset + index,
                url_template=self.config.chat_url_template,
            )
            for index, chat in enumerate(page.chats if page else [])
        ]
        return self._sources_response(
            call_id, sources, next_page=arguments.page + 1 if has_more else None
        )

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _current_chat_ids(event: ChatEvent) -> list[str]:
        chat_ids = [event.payload.chat_id]
        correlation = event.payload.correlation
        if correlation and correlation.parent_chat_id not in chat_ids:
            chat_ids.append(correlation.parent_chat_id)
        return chat_ids

    @staticmethod
    def _window(
        arguments: ProjectChatSearchInput,
    ) -> tuple[datetime | None, datetime | None]:
        try:
            after = (
                parse_day(arguments.after, end_of_day=False)
                if arguments.after
                else None
            )
            before = (
                parse_day(arguments.before, end_of_day=True)
                if arguments.before
                else None
            )
        except ValueError as error:
            raise _Correction(
                "`after` and `before` must be days like 2026-11-24."
            ) from error
        return after, before

    def _check_page(self, page: int) -> None:
        if page > self.config.max_page:
            raise _Correction(
                f"`page` can be at most {self.config.max_page}. "
                'Narrow it down with mode "search" instead.'
            )

    async def _walk_to_page[PageT: ProjectChatChunkPage | ProjectChatSummaryPage](
        self,
        fetch: _Fetch[PageT],
        page_number: int,
    ) -> tuple[PageT | None, bool]:
        """Follow the endpoint's cursors to page ``page_number`` (from 1).

        Returns:
            The page, or ``None`` when there are fewer pages, and whether a
            further page exists.
        """
        cursor: str | None = None
        for _ in range(page_number - 1):
            skipped = await fetch(cursor)
            cursor = skipped.next_cursor
            if cursor is None:
                return None, False
        page = await fetch(cursor)
        return page, page.next_cursor is not None

    def _sources_response(
        self, call_id: str, sources: list[ContentChunk], *, next_page: int | None
    ) -> ToolCallResponse:
        kept, omitted = fit_to_budget(sources, self.config.max_tokens)
        reminders: list[str] = []
        if omitted:
            reminders.append(
                f"{omitted} more result(s) were left out to stay within the "
                "token budget; search for something more specific to see them."
            )
        if next_page is not None:
            if next_page <= self.config.max_page:
                reminders.append(
                    "More results: call ProjectChatSearch again with the same "
                    f"fields and page={next_page}."
                )
            else:
                reminders.append(
                    'There are more results; use mode "search" to find specific ones.'
                )
        return self._response(
            call_id, content_chunks=kept, system_reminder="\n".join(reminders)
        )

    def _response(
        self,
        call_id: str,
        *,
        content: str = "",
        content_chunks: list[ContentChunk] | None = None,
        error_message: str = "",
        system_reminder: str = "",
    ) -> ToolCallResponse:
        return ToolCallResponse(
            id=call_id,
            name=self.name,
            content=content,
            content_chunks=content_chunks or [],
            error_message=error_message,
            system_reminder=system_reminder,
        )


ToolFactory.register_tool(ProjectChatSearchTool, ProjectChatSearchConfig)
