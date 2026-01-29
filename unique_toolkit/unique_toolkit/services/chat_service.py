import logging
from typing import Any, Sequence, overload

import unique_sdk
from openai.types.chat import ChatCompletionToolChoiceOptionParam
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.responses import (
    ResponseIncludable,
    ResponseInputItemParam,
    ResponseOutputItem,
    ResponseTextConfigParam,
    ToolParam,
    response_create_params,
)
from openai.types.shared_params import Metadata, Reasoning
from pydantic import BaseModel
from typing_extensions import deprecated

from unique_toolkit._common.utils.files import is_file_content, is_image_content
from unique_toolkit.chat.constants import (
    DEFAULT_MAX_MESSAGES,
    DEFAULT_PERCENT_OF_MAX_TOKENS,
    DOMAIN_NAME,
)
from unique_toolkit.chat.deprecated.service import ChatServiceDeprecated
from unique_toolkit.chat.functions import (
    create_message,
    create_message_assessment,
    create_message_assessment_async,
    create_message_async,
    create_message_execution,
    create_message_execution_async,
    create_message_log,
    create_message_log_async,
    get_full_history,
    get_full_history_async,
    get_message_execution,
    get_message_execution_async,
    get_selection_from_history,
    modify_message,
    modify_message_assessment,
    modify_message_assessment_async,
    modify_message_async,
    stream_complete_with_references,
    stream_complete_with_references_async,
    update_message_execution,
    update_message_execution_async,
    update_message_log,
    update_message_log_async,
)
from unique_toolkit.chat.responses_api import (
    stream_responses_with_references,
    stream_responses_with_references_async,
)
from unique_toolkit.chat.schemas import (
    ChatMessage,
    ChatMessageAssessment,
    ChatMessageAssessmentLabel,
    ChatMessageAssessmentStatus,
    ChatMessageAssessmentType,
    ChatMessageRole,
    MessageExecution,
    MessageExecutionType,
    MessageExecutionUpdateStatus,
    MessageLog,
    MessageLogDetails,
    MessageLogStatus,
    MessageLogUncitedReferences,
)
from unique_toolkit.content.functions import (
    download_content_to_bytes,
    search_contents,
    upload_content_from_bytes,
    upload_content_from_bytes_async,
)
from unique_toolkit.content.schemas import (
    Content,
    ContentChunk,
    ContentReference,
)
from unique_toolkit.language_model.constants import (
    DEFAULT_COMPLETE_TEMPERATURE,
    DEFAULT_COMPLETE_TIMEOUT,
)
from unique_toolkit.language_model.infos import (
    LanguageModelInfo,
    LanguageModelName,
)
from unique_toolkit.language_model.schemas import (
    LanguageModelMessageOptions,
    LanguageModelMessages,
    LanguageModelResponse,
    LanguageModelStreamResponse,
    LanguageModelTool,
    LanguageModelToolDescription,
    ResponsesLanguageModelStreamResponse,
)
from unique_toolkit.short_term_memory.functions import (
    create_memory,
    create_memory_async,
    find_latest_memory,
    find_latest_memory_async,
)
from unique_toolkit.short_term_memory.schemas import ShortTermMemory

logger = logging.getLogger(f"toolkit.{DOMAIN_NAME}.{__name__}")


class ChatService(ChatServiceDeprecated):
    """Provides all functionalities to manage the chat session."""

    async def update_debug_info_async(self, debug_info: dict):
        """Updates the debug information for the chat session.

        Args:
            debug_info (dict): The new debug information.

        """
        return await modify_message_async(
            user_id=self._user_id,
            company_id=self._company_id,
            assistant_message_id=self._assistant_message_id,
            chat_id=self._chat_id,
            user_message_id=self._user_message_id,
            user_message_text=self._user_message_text,
            assistant=False,
            debug_info=debug_info,
        )

    def replace_debug_info(self, debug_info: dict):
        """Replace the debug information in the last user message

        Args:
            debug_info (dict): The new debug information.

        """
        return modify_message(
            user_id=self._user_id,
            company_id=self._company_id,
            assistant_message_id=self._assistant_message_id,
            chat_id=self._chat_id,
            user_message_id=self._user_message_id,
            user_message_text=self._user_message_text,
            assistant=False,
            debug_info=debug_info,
        )

    # Message Methods
    ############################################################################

    def modify_user_message(
        self,
        content: str,
        references: list[ContentReference] | None = None,
        debug_info: dict | None = None,
        message_id: str | None = None,
        set_completed_at: bool | None = False,
    ) -> ChatMessage:
        """Modifies a user message in the chat session synchronously.

        Args:
            content (str): The new content for the message.
            references (list[ContentReference]): list of ContentReference objects.
            debug_info (dict[str, Any]]]): Debug information.
            message_id (str, optional): The message ID, if not specified the last user message is edited.
            set_completed_at (Optional[bool]): Whether to set the completedAt field with the current date time. Defaults to False.

        Returns:
            ChatMessage: The modified message.

        Raises:
            Exception: If the modification fails.

        """
        return modify_message(
            user_id=self._user_id,
            company_id=self._company_id,
            assistant_message_id=self._assistant_message_id,
            chat_id=self._chat_id,
            user_message_id=self._user_message_id,
            user_message_text=self._user_message_text,
            assistant=False,
            content=content,
            references=references,
            debug_info=debug_info,
            message_id=message_id,
            set_completed_at=set_completed_at or False,
        )

    async def modify_user_message_async(
        self,
        content: str,
        references: list[ContentReference] = [],
        debug_info: dict = {},
        message_id: str | None = None,
        set_completed_at: bool | None = False,
    ) -> ChatMessage:
        """Modifies a message in the chat session asynchronously.

        Args:
            content (str): The new content for the message.
            message_id (str, optional): The message ID. Defaults to None, then the ChatState user message id is used.
            references (list[ContentReference]): list of ContentReference objects. Defaults to None.
            debug_info (dict[str, Any]]]): Debug information. Defaults to {}.
            set_completed_at (bool, optional): Whether to set the completedAt field with the current date time. Defaults to False.

        Returns:
            ChatMessage: The modified message.

        Raises:
            Exception: If the modification fails.

        """
        return await modify_message_async(
            user_id=self._user_id,
            company_id=self._company_id,
            assistant_message_id=self._assistant_message_id,
            chat_id=self._chat_id,
            user_message_id=self._user_message_id,
            user_message_text=self._user_message_text,
            assistant=False,
            content=content,
            references=references,
            debug_info=debug_info,
            message_id=message_id,
            set_completed_at=set_completed_at or False,
        )

    def modify_assistant_message(
        self,
        content: str | None = None,
        original_content: str | None = None,
        references: list[ContentReference] | None = None,
        debug_info: dict | None = None,
        message_id: str | None = None,
        set_completed_at: bool | None = None,
    ) -> ChatMessage:
        """Modifies a message in the chat session synchronously if parameter is not specified the corresponding field will remain as is.

        Args:
            content (str, optional): The new content for the message.
            original_content (str, optional): The original content for the message.
            references (list[ContentReference]): list of ContentReference objects. Defaults to [].
            debug_info (dict[str, Any]]]): Debug information. Defaults to {}.
            message_id (Optional[str]): The message ID. Defaults to None.
            set_completed_at (Optional[bool]): Whether to set the completedAt field with the current date time. Defaults to False.

        Returns:
            ChatMessage: The modified message.

        Raises:
            Exception: If the modification fails.

        """

        return modify_message(
            user_id=self._user_id,
            company_id=self._company_id,
            assistant_message_id=self._assistant_message_id,
            chat_id=self._chat_id,
            user_message_id=self._user_message_id,
            user_message_text=self._user_message_text,
            assistant=True,
            content=content,
            original_content=original_content,
            references=references,
            debug_info=debug_info,
            message_id=message_id,
            set_completed_at=set_completed_at or False,
        )

    async def modify_assistant_message_async(
        self,
        content: str | None = None,
        original_content: str | None = None,
        references: list[ContentReference] | None = None,
        debug_info: dict | None = None,
        message_id: str | None = None,
        set_completed_at: bool | None = False,
    ) -> ChatMessage:
        """Modifies a message in the chat session asynchronously.

        Args:
            content (str, optional): The new content for the message.
            original_content (str, optional): The original content for the message.
            message_id (str, optional): The message ID. Defaults to None, then the ChatState assistant message id is used.
            references (list[ContentReference]): list of ContentReference objects. Defaults to None.
            debug_info (dict[str, Any]], optional): Debug information. Defaults to None.
            set_completed_at (bool, optional): Whether to set the completedAt field with the current date time. Defaults to False.

        Returns:
            ChatMessage: The modified message.

        Raises:
            Exception: If the modification fails.

        """
        return await modify_message_async(
            user_id=self._user_id,
            company_id=self._company_id,
            assistant_message_id=self._assistant_message_id,
            chat_id=self._chat_id,
            user_message_id=self._user_message_id,
            user_message_text=self._user_message_text,
            assistant=True,
            content=content,
            original_content=original_content,
            references=references,
            debug_info=debug_info,
            message_id=message_id,
            set_completed_at=set_completed_at or False,
        )

    def create_assistant_message(
        self,
        content: str,
        original_content: str | None = None,
        references: list[ContentReference] | None = None,
        debug_info: dict | None = None,
        set_completed_at: bool | None = False,
    ) -> ChatMessage:
        """Creates a message in the chat session synchronously.

        Args:
            content (str): The content for the message.
            original_content (str, optional): The original content for the message.
            references (list[ContentReference]): list of ContentReference objects. Defaults to None.
            debug_info (dict[str, Any]]): Debug information. Defaults to None.
            set_completed_at (Optional[bool]): Whether to set the completedAt field with the current date time. Defaults to False.

        Returns:
            ChatMessage: The created message.

        Raises:
            Exception: If the creation fails.

        """
        chat_message = create_message(
            user_id=self._user_id,
            company_id=self._company_id,
            chat_id=self._chat_id,
            assistant_id=self._assistant_id,
            role=ChatMessageRole.ASSISTANT,
            content=content,
            original_content=original_content,
            references=references,
            debug_info=debug_info,
            set_completed_at=set_completed_at,
        )
        # Update the assistant message id
        self._assistant_message_id = chat_message.id or "unknown"
        return chat_message

    async def create_assistant_message_async(
        self,
        content: str,
        original_content: str | None = None,
        references: list[ContentReference] | None = None,
        debug_info: dict | None = None,
        set_completed_at: bool | None = False,
    ) -> ChatMessage:
        """Creates a message in the chat session asynchronously.

        Args:
            content (str): The content for the message.
            original_content (str, optional): The original content for the message.
            references (list[ContentReference]): list of references. Defaults to None.
            debug_info (dict[str, Any]]): Debug information. Defaults to None.
            set_completed_at (Optional[bool]): Whether to set the completedAt field with the current date time. Defaults to False.

        Returns:
            ChatMessage: The created message.

        Raises:
            Exception: If the creation fails.

        """
        chat_message = await create_message_async(
            user_id=self._user_id,
            company_id=self._company_id,
            chat_id=self._chat_id,
            assistant_id=self._assistant_id,
            role=ChatMessageRole.ASSISTANT,
            content=content,
            original_content=original_content,
            references=references,
            debug_info=debug_info,
            set_completed_at=set_completed_at,
        )
        # Update the assistant message id
        self._assistant_message_id = chat_message.id or "unknown"
        return chat_message

    def create_user_message(
        self,
        content: str,
        original_content: str | None = None,
        references: list[ContentReference] | None = None,
        debug_info: dict | None = None,
        set_completed_at: bool | None = False,
    ) -> ChatMessage:
        """Creates a user message in the chat session synchronously.

        Args:
            content (str): The content for the message.
            original_content (str, optional): The original content for the message.
            references (list[ContentReference]): list of ContentReference objects. Defaults to None.
            debug_info (dict[str, Any]]): Debug information. Defaults to None.
            set_completed_at (Optional[bool]): Whether to set the completedAt field with the current date time. Defaults to False.

        Returns:
            ChatMessage: The created message.

        Raises:
            Exception: If the creation fails.

        """
        chat_message = create_message(
            user_id=self._user_id,
            company_id=self._company_id,
            chat_id=self._chat_id,
            assistant_id=self._assistant_id,
            role=ChatMessageRole.USER,
            content=content,
            original_content=original_content,
            references=references,
            debug_info=debug_info,
            set_completed_at=set_completed_at,
        )
        # Update the user message id
        self._user_message_id = chat_message.id or "unknown"
        return chat_message

    async def create_user_message_async(
        self,
        content: str,
        original_content: str | None = None,
        references: list[ContentReference] | None = None,
        debug_info: dict | None = None,
        set_completed_at: bool | None = False,
    ) -> ChatMessage:
        """Creates a user message in the chat session asynchronously.

        Args:
            content (str): The content for the message.
            original_content (str, optional): The original content for the message.
            references (list[ContentReference]): list of references. Defaults to None.
            debug_info (dict[str, Any]]): Debug information. Defaults to None.
            set_completed_at (Optional[bool]): Whether to set the completedAt field with the current date time. Defaults to False.

        Returns:
            ChatMessage: The created message.

        Raises:
            Exception: If the creation fails.

        """
        chat_message = await create_message_async(
            user_id=self._user_id,
            company_id=self._company_id,
            chat_id=self._chat_id,
            assistant_id=self._assistant_id,
            role=ChatMessageRole.USER,
            content=content,
            original_content=original_content,
            references=references,
            debug_info=debug_info,
            set_completed_at=set_completed_at,
        )
        # Update the user message id
        self._user_message_id = chat_message.id or "unknown"
        return chat_message

    def free_user_input(self) -> None:
        """Unblocks the next user input"""
        self.modify_assistant_message(set_completed_at=True)

    # History Methods
    ############################################################################

    def get_full_history(self) -> list[ChatMessage]:
        """Loads the full chat history for the chat session synchronously.

        Returns:
            list[ChatMessage]: The full chat history.

        Raises:
            Exception: If the loading fails.

        """
        return get_full_history(
            event_user_id=self._user_id,
            event_company_id=self._company_id,
            event_payload_chat_id=self._chat_id,
        )

    async def get_full_history_async(self) -> list[ChatMessage]:
        """Loads the full chat history for the chat session asynchronously.

        Returns:
            list[ChatMessage]: The full chat history.

        Raises:
            Exception: If the loading fails.

        """
        return await get_full_history_async(
            event_user_id=self._user_id,
            event_company_id=self._company_id,
            event_payload_chat_id=self._chat_id,
        )

    def get_full_and_selected_history(
        self,
        token_limit: int,
        percent_of_max_tokens: float = DEFAULT_PERCENT_OF_MAX_TOKENS,
        max_messages: int = DEFAULT_MAX_MESSAGES,
        model_info: LanguageModelInfo | None = None,
    ) -> tuple[list[ChatMessage], list[ChatMessage]]:
        """Loads the chat history for the chat session synchronously.

        Args:
            token_limit (int): The maximum number of tokens to load.
            percent_of_max_tokens (float): The percentage of the maximum tokens to load. Defaults to 0.15.
            max_messages (int): The maximum number of messages to load. Defaults to 4.
            model_info (LanguageModelInfo | None): Optional model info for accurate token counting.

        Returns:
            tuple[list[ChatMessage], list[ChatMessage]]: The selected and full chat history.

        Raises:
            Exception: If the loading fails.

        """
        full_history = get_full_history(
            event_user_id=self._user_id,
            event_company_id=self._company_id,
            event_payload_chat_id=self._chat_id,
        )
        selected_history = get_selection_from_history(
            full_history=full_history,
            max_tokens=int(round(token_limit * percent_of_max_tokens)),
            max_messages=max_messages,
            model_info=model_info,
        )

        return full_history, selected_history

    async def get_full_and_selected_history_async(
        self,
        token_limit: int,
        percent_of_max_tokens: float = DEFAULT_PERCENT_OF_MAX_TOKENS,
        max_messages: int = DEFAULT_MAX_MESSAGES,
        model_info: LanguageModelInfo | None = None,
    ) -> tuple[list[ChatMessage], list[ChatMessage]]:
        """Loads the chat history for the chat session asynchronously.

        Args:
            token_limit (int): The maximum number of tokens to load.
            percent_of_max_tokens (float): The percentage of the maximum tokens to load. Defaults to 0.15.
            max_messages (int): The maximum number of messages to load. Defaults to 4.
            model_info (LanguageModelInfo | None): Optional model info for accurate token counting.

        Returns:
            tuple[list[ChatMessage], list[ChatMessage]]: The selected and full chat history.

        Raises:
            Exception: If the loading fails.

        """
        full_history = await get_full_history_async(
            event_user_id=self._user_id,
            event_company_id=self._company_id,
            event_payload_chat_id=self._chat_id,
        )
        selected_history = get_selection_from_history(
            full_history=full_history,
            max_tokens=int(round(token_limit * percent_of_max_tokens)),
            max_messages=max_messages,
            model_info=model_info,
        )

        return full_history, selected_history

    # Message Assessment Methods
    ############################################################################

    def create_message_assessment(
        self,
        assistant_message_id: str,
        status: ChatMessageAssessmentStatus,
        type: ChatMessageAssessmentType,
        title: str | None = None,
        explanation: str | None = None,
        label: ChatMessageAssessmentLabel | None = None,
        is_visible: bool = True,
    ) -> ChatMessageAssessment:
        """Creates a message assessment for an assistant message synchronously.

        Args:
            assistant_message_id (str): The ID of the assistant message to assess
            status (MessageAssessmentStatus): The status of the assessment (e.g. "DONE")
            type (MessageAssessmentType): The type of assessment (e.g. "HALLUCINATION")
            title (str | None): The title of the assessment
            explanation (str | None): Explanation of the assessment
            label (MessageAssessmentLabel | None): The assessment label (e.g. "RED")
            is_visible (bool): Whether the assessment is visible to users. Defaults to True.

        Returns:
            ChatMessageAssessment: The created message assessment

        Raises:
            Exception: If the creation fails

        """
        return create_message_assessment(
            user_id=self._user_id,
            company_id=self._company_id,
            assistant_message_id=assistant_message_id,
            status=status,
            type=type,
            title=title,
            explanation=explanation,
            label=label,
            is_visible=is_visible,
        )

    async def create_message_assessment_async(
        self,
        assistant_message_id: str,
        status: ChatMessageAssessmentStatus,
        type: ChatMessageAssessmentType,
        title: str | None = None,
        explanation: str | None = None,
        label: ChatMessageAssessmentLabel | None = None,
        is_visible: bool = True,
    ) -> ChatMessageAssessment:
        """Creates a message assessment for an assistant message asynchronously.

        Args:
            assistant_message_id (str): The ID of the assistant message to assess
            status (ChatMessageAssessmentStatus): The status of the assessment (e.g. "DONE")
            type (ChatMessageAssessmentType): The type of assessment (e.g. "HALLUCINATION")
            title (str | None): The title of the assessment
            explanation (str | None): Explanation of the assessment
            label (ChatMessageAssessmentLabel | None): The assessment label (e.g. "RED")
            is_visible (bool): Whether the assessment is visible to users. Defaults to True.

        Returns:
            ChatMessageAssessment: The created message assessment

        Raises:
            Exception: If the creation fails

        """
        return await create_message_assessment_async(
            user_id=self._user_id,
            company_id=self._company_id,
            assistant_message_id=assistant_message_id,
            status=status,
            type=type,
            title=title,
            explanation=explanation,
            label=label,
            is_visible=is_visible,
        )

    def modify_message_assessment(
        self,
        assistant_message_id: str,
        status: ChatMessageAssessmentStatus,
        type: ChatMessageAssessmentType,
        title: str | None = None,
        explanation: str | None = None,
        label: ChatMessageAssessmentLabel | None = None,
    ) -> ChatMessageAssessment:
        """Modifies a message assessment for an assistant message synchronously.

        Args:
            assistant_message_id (str): The ID of the assistant message to assess
            status (MessageAssessmentStatus): The status of the assessment (e.g. "DONE")
            title (str | None): The title of the assessment
            explanation (str | None): Explanation of the assessment
            label (ChatMessageAssessmentLabel | None): The assessment label (e.g. "RED")
            type (ChatMessageAssessmentType): The type of assessment (e.g. "HALLUCINATION")

        Returns:
            dict: The modified message assessment

        Raises:
            Exception: If the modification fails

        """
        return modify_message_assessment(
            user_id=self._user_id,
            company_id=self._company_id,
            assistant_message_id=assistant_message_id,
            status=status,
            type=type,
            title=title,
            explanation=explanation,
            label=label,
        )

    async def modify_message_assessment_async(
        self,
        assistant_message_id: str,
        type: ChatMessageAssessmentType,
        title: str | None = None,
        status: ChatMessageAssessmentStatus | None = None,
        explanation: str | None = None,
        label: ChatMessageAssessmentLabel | None = None,
    ) -> ChatMessageAssessment:
        """Modifies a message assessment for an assistant message asynchronously.

        Args:
            assistant_message_id (str): The ID of the assistant message to assess
            status (ChatMessageAssessmentStatus): The status of the assessment (e.g. "DONE")
            title (str | None): The title of the assessment
            explanation (str | None): Explanation of the assessment
            label (ChatMessageAssessmentLabel | None): The assessment label (e.g. "RED")
            type (ChatMessageAssessmentType): The type of assessment (e.g. "HALLUCINATION")

        Returns:
            ChatMessageAssessment: The modified message assessment

        Raises:
            Exception: If the modification fails

        """
        return await modify_message_assessment_async(
            user_id=self._user_id,
            company_id=self._company_id,
            assistant_message_id=assistant_message_id,
            status=status,
            type=type,
            title=title,
            explanation=explanation,
            label=label,
        )

    # Message Log Methods
    ############################################################################

    def create_message_log(
        self,
        *,
        message_id: str,
        text: str,
        status: MessageLogStatus,
        order: int,
        details: MessageLogDetails | None = None,
        uncited_references: MessageLogUncitedReferences | None = None,
        references: list[ContentReference] | None = None,
    ) -> MessageLog:
        """Creates a message log for tracking execution steps synchronously.

        Args:
            message_id (str): The ID of the message this log belongs to
            text (str): The log text content
            status (MessageLogStatus): The status of this log entry
            order (int): The order/sequence number of this log entry
            details (MessageLogDetails | None): Additional details about this log entry
            uncited_references (MessageLogUncitedReferences | None): References that are not cited
            references (list[ContentReference] | None): List of references for this log

        Returns:
            MessageLog: The created message log

        Raises:
            Exception: If the creation fails

        """
        return create_message_log(
            user_id=self._user_id,
            company_id=self._company_id,
            message_id=message_id,
            text=text,
            status=status,
            order=order,
            details=details,
            uncited_references=uncited_references,
            references=references,
        )

    async def create_message_log_async(
        self,
        *,
        message_id: str,
        text: str,
        status: MessageLogStatus,
        order: int,
        details: MessageLogDetails | None = None,
        uncited_references: MessageLogUncitedReferences | None = None,
        references: list[ContentReference] | None = None,
    ) -> MessageLog:
        """Creates a message log for tracking execution steps asynchronously.

        Args:
            message_id (str): The ID of the message this log belongs to
            text (str): The log text content
            status (MessageLogStatus): The status of this log entry
            order (int): The order/sequence number of this log entry
            details (MessageLogDetails | None): Additional details about this log entry
            uncited_references (MessageLogUncitedReferences | None): References that are not cited
            references (list[ContentReference] | None): List of references for this log

        Returns:
            MessageLog: The created message log

        Raises:
            Exception: If the creation fails

        """
        return await create_message_log_async(
            user_id=self._user_id,
            company_id=self._company_id,
            message_id=message_id,
            text=text,
            status=status,
            order=order,
            details=details,
            uncited_references=uncited_references,
            references=references,
        )

    def update_message_log(
        self,
        *,
        message_log_id: str,
        order: int,
        text: str | None = None,
        status: MessageLogStatus | None = None,
        details: MessageLogDetails | None = None,
        uncited_references: MessageLogUncitedReferences | None = None,
        references: list[ContentReference] | None = None,
    ) -> MessageLog:
        """Updates a message log synchronously.

        Args:
            message_log_id (str): The ID of the message log to update
            order (int): The order/sequence number (required)
            text (str | None): The updated log text content
            status (MessageLogStatus | None): The updated status
            details (MessageLogDetails | None): Updated additional details
            uncited_references (MessageLogUncitedReferences | None): Updated uncited references
            references (list[ContentReference] | None): Updated list of references

        Returns:
            MessageLog: The updated message log

        Raises:
            Exception: If the update fails

        """
        return update_message_log(
            user_id=self._user_id,
            company_id=self._company_id,
            message_log_id=message_log_id,
            order=order,
            text=text,
            status=status,
            details=details,
            uncited_references=uncited_references,
            references=references,
        )

    async def update_message_log_async(
        self,
        *,
        message_log_id: str,
        order: int,
        text: str | None = None,
        status: MessageLogStatus | None = None,
        details: MessageLogDetails | None = None,
        uncited_references: MessageLogUncitedReferences | None = None,
        references: list[ContentReference] | None = None,
    ) -> MessageLog:
        """Updates a message log asynchronously.

        Args:
            message_log_id (str): The ID of the message log to update
            order (int): The order/sequence number (required)
            text (str | None): The updated log text content
            status (MessageLogStatus | None): The updated status
            details (MessageLogDetails | None): Updated additional details
            uncited_references (MessageLogUncitedReferences | None): Updated uncited references
            references (list[ContentReference] | None): Updated list of references

        Returns:
            MessageLog: The updated message log

        Raises:
            Exception: If the update fails

        """
        return await update_message_log_async(
            user_id=self._user_id,
            company_id=self._company_id,
            message_log_id=message_log_id,
            order=order,
            text=text,
            status=status,
            details=details,
            uncited_references=uncited_references,
            references=references,
        )

    def create_assistant_message_log(
        self,
        *,
        text: str,
        status: MessageLogStatus,
        order: int,
        details: MessageLogDetails | None = None,
        uncited_references: MessageLogUncitedReferences | None = None,
        references: list[ContentReference] | None = None,
    ) -> MessageLog:
        """Creates a message log for the current assistant message synchronously.

        This is a convenience method that uses the current assistant message ID.

        Args:
            text (str): The log text content
            status (MessageLogStatus): The status of this log entry
            order (int): The order/sequence number of this log entry
            details (MessageLogDetails | None): Additional details about this log entry
            uncited_references (MessageLogUncitedReferences | None): References that are not cited
            references (list[ContentReference] | None): List of references for this log

        Returns:
            MessageLog: The created message log

        Raises:
            Exception: If the creation fails

        """
        return self.create_message_log(
            message_id=self._assistant_message_id,
            text=text,
            status=status,
            order=order,
            details=details,
            uncited_references=uncited_references,
            references=references,
        )

    async def create_assistant_message_log_async(
        self,
        *,
        text: str,
        status: MessageLogStatus,
        order: int,
        details: MessageLogDetails | None = None,
        uncited_references: MessageLogUncitedReferences | None = None,
        references: list[ContentReference] | None = None,
    ) -> MessageLog:
        """Creates a message log for the current assistant message asynchronously.

        This is a convenience method that uses the current assistant message ID.

        Args:
            text (str): The log text content
            status (MessageLogStatus): The status of this log entry
            order (int): The order/sequence number of this log entry
            details (MessageLogDetails | None): Additional details about this log entry
            uncited_references (MessageLogUncitedReferences | None): References that are not cited
            references (list[ContentReference] | None): List of references for this log

        Returns:
            MessageLog: The created message log

        Raises:
            Exception: If the creation fails

        """
        return await self.create_message_log_async(
            message_id=self._assistant_message_id,
            text=text,
            status=status,
            order=order,
            details=details,
            uncited_references=uncited_references,
            references=references,
        )

    # Message Execution Methods
    ############################################################################

    def create_message_execution(
        self,
        *,
        message_id: str,
        type: MessageExecutionType = MessageExecutionType.DEEP_RESEARCH,
        seconds_remaining: int | None = None,
        percentage_completed: int | None = None,
        is_queueable: bool = True,
        execution_options: dict | None = None,
        progress_title: str | None = None,
    ) -> MessageExecution:
        """Creates a message execution for tracking long-running operations synchronously.

        Args:
            message_id (str): The ID of the message this execution belongs to
            type (MessageExecutionType): The type of execution. Defaults to DEEP_RESEARCH.
            seconds_remaining (int | None): Estimated seconds remaining for completion
            percentage_completed (int | None): Percentage of completion (0-100)
            is_queueable (bool): Whether the execution is queueable. Defaults to True. If true, then the progress will be updated in the background by the execution pipeline. Set to False if you want to update the progress manually.
            execution_options (dict | None): Additional execution options. Defaults to None.
            progress_title (str | None): The title of the progress bar. If not provided, the title of the last message log is taken.

        Returns:
            MessageExecution: The created message execution

        Raises:
            Exception: If the creation fails

        """
        return create_message_execution(
            user_id=self._user_id,
            company_id=self._company_id,
            message_id=message_id,
            chat_id=self._chat_id,
            type=type,
            seconds_remaining=seconds_remaining,
            percentage_completed=percentage_completed,
            is_queueable=is_queueable,
            execution_options=execution_options,
            progress_title=progress_title,
        )

    async def create_message_execution_async(
        self,
        *,
        message_id: str,
        type: MessageExecutionType = MessageExecutionType.DEEP_RESEARCH,
        seconds_remaining: int | None = None,
        percentage_completed: int | None = None,
        is_queueable: bool = True,
        execution_options: dict | None = None,
        progress_title: str | None = None,
    ) -> MessageExecution:
        """Creates a message execution for tracking long-running operations asynchronously.

        Args:
            message_id (str): The ID of the message this execution belongs to
            type (MessageExecutionType): The type of execution. Defaults to DEEP_RESEARCH.
            seconds_remaining (int | None): Estimated seconds remaining for completion
            percentage_completed (int | None): Percentage of completion (0-100)
            is_queueable (bool): Whether the execution is queueable. Defaults to True. If true, then the progress will be updated in the background by the execution pipeline. Set to False if you want to update the progress manually.
            execution_options (dict | None): Additional execution options. Defaults to None.
            progress_title (str | None): The title of the progress bar. If not provided, the title of the last message log is taken.

        Returns:
            MessageExecution: The created message execution

        Raises:
            Exception: If the creation fails

        """
        return await create_message_execution_async(
            user_id=self._user_id,
            company_id=self._company_id,
            message_id=message_id,
            chat_id=self._chat_id,
            type=type,
            seconds_remaining=seconds_remaining,
            percentage_completed=percentage_completed,
            is_queueable=is_queueable,
            execution_options=execution_options,
            progress_title=progress_title,
        )

    def get_message_execution(
        self,
        *,
        message_id: str,
    ) -> MessageExecution:
        """Gets a message execution by message ID synchronously.

        Args:
            message_id (str): The ID of the message to get execution for

        Returns:
            MessageExecution: The message execution

        Raises:
            Exception: If the retrieval fails

        """
        return get_message_execution(
            user_id=self._user_id,
            company_id=self._company_id,
            message_id=message_id,
        )

    async def get_message_execution_async(
        self,
        *,
        message_id: str,
    ) -> MessageExecution:
        """Gets a message execution by message ID asynchronously.

        Args:
            message_id (str): The ID of the message to get execution for

        Returns:
            MessageExecution: The message execution

        Raises:
            Exception: If the retrieval fails

        """
        return await get_message_execution_async(
            user_id=self._user_id,
            company_id=self._company_id,
            message_id=message_id,
        )

    def update_message_execution(
        self,
        *,
        message_id: str,
        status: MessageExecutionUpdateStatus | None = None,
        seconds_remaining: int | None = None,
        percentage_completed: int | None = None,
        progress_title: str | None = None,
    ) -> MessageExecution:
        """Updates a message execution synchronously.

        Args:
            message_id (str): The ID of the message to update execution for
            status (MessageExecutionUpdateStatus | None): The updated status (COMPLETED or FAILED). Defaults to None
            seconds_remaining (int | None): Updated estimated seconds remaining
            percentage_completed (int | None): Updated percentage of completion (0-100)
            progress_title (str | None): The title of the progress bar. If not provided, the title of the last message log is taken.

        Returns:
            MessageExecution: The updated message execution

        Raises:
            Exception: If the update fails

        """
        return update_message_execution(
            user_id=self._user_id,
            company_id=self._company_id,
            message_id=message_id,
            status=status,
            seconds_remaining=seconds_remaining,
            percentage_completed=percentage_completed,
            progress_title=progress_title,
        )

    async def update_message_execution_async(
        self,
        *,
        message_id: str,
        status: MessageExecutionUpdateStatus | None = None,
        seconds_remaining: int | None = None,
        percentage_completed: int | None = None,
        progress_title: str | None = None,
    ) -> MessageExecution:
        """Updates a message execution asynchronously.

        Args:
            message_id (str): The ID of the message to update execution for
            status (MessageExecutionUpdateStatus | None): The updated status (COMPLETED or FAILED). Defaults to None
            seconds_remaining (int | None): Updated estimated seconds remaining
            percentage_completed (int | None): Updated percentage of completion (0-100)
            progress_title (str | None): The title of the progress bar. If not provided, the title of the last message log is taken.

        Returns:
            MessageExecution: The updated message execution

        Raises:
            Exception: If the update fails

        """
        return await update_message_execution_async(
            user_id=self._user_id,
            company_id=self._company_id,
            message_id=message_id,
            status=status,
            seconds_remaining=seconds_remaining,
            percentage_completed=percentage_completed,
            progress_title=progress_title,
        )

    def create_assistant_message_execution(
        self,
        *,
        type: MessageExecutionType = MessageExecutionType.DEEP_RESEARCH,
        seconds_remaining: int | None = None,
        percentage_completed: int | None = None,
        is_queueable: bool = True,
        execution_options: dict | None = None,
        progress_title: str | None = None,
    ) -> MessageExecution:
        """Creates a message execution for the current assistant message synchronously.

        This is a convenience method that uses the current assistant message ID.

        Args:
            type (MessageExecutionType): The type of execution. Defaults to DEEP_RESEARCH.
            seconds_remaining (int | None): Estimated seconds remaining for completion
            percentage_completed (int | None): Percentage of completion (0-100)
            is_queueable (bool): Whether the execution is queueable. Defaults to True. If true, then the progress will be updated in the background by the execution pipeline. Set to False if you want to update the progress manually.
            execution_options (dict | None): Additional execution options. Defaults to None.
            progress_title (str | None): The title of the progress bar. If not provided, the title of the last message log is taken.

        Returns:
            MessageExecution: The created message execution

        Raises:
            Exception: If the creation fails

        """
        return self.create_message_execution(
            message_id=self._assistant_message_id,
            type=type,
            seconds_remaining=seconds_remaining,
            percentage_completed=percentage_completed,
            is_queueable=is_queueable,
            execution_options=execution_options,
            progress_title=progress_title,
        )

    async def create_assistant_message_execution_async(
        self,
        *,
        type: MessageExecutionType = MessageExecutionType.DEEP_RESEARCH,
        seconds_remaining: int | None = None,
        percentage_completed: int | None = None,
        is_queueable: bool = True,
        execution_options: dict | None = None,
        progress_title: str | None = None,
    ) -> MessageExecution:
        """Creates a message execution for the current assistant message asynchronously.

        This is a convenience method that uses the current assistant message ID.

        Args:
            type (MessageExecutionType): The type of execution. Defaults to DEEP_RESEARCH.
            seconds_remaining (int | None): Estimated seconds remaining for completion
            percentage_completed (int | None): Percentage of completion (0-100)
            is_queueable (bool): Whether the execution is queueable. Defaults to True. If true, then the progress will be updated in the background by the execution pipeline. Set to False if you want to update the progress manually.
            execution_options (dict | None): Additional execution options. Defaults to None.
            progress_title (str | None): The title of the progress bar. If not provided, the title of the last message log is taken.

        Returns:
            MessageExecution: The created message execution

        Raises:
            Exception: If the creation fails

        """
        return await self.create_message_execution_async(
            message_id=self._assistant_message_id,
            type=type,
            seconds_remaining=seconds_remaining,
            percentage_completed=percentage_completed,
            is_queueable=is_queueable,
            execution_options=execution_options,
            progress_title=progress_title,
        )

    def get_assistant_message_execution(self) -> MessageExecution:
        """Gets the message execution for the current assistant message synchronously.

        This is a convenience method that uses the current assistant message ID.

        Returns:
            MessageExecution: The message execution

        Raises:
            Exception: If the retrieval fails

        """
        return self.get_message_execution(message_id=self._assistant_message_id)

    async def get_assistant_message_execution_async(self) -> MessageExecution:
        """Gets the message execution for the current assistant message asynchronously.

        This is a convenience method that uses the current assistant message ID.

        Returns:
            MessageExecution: The message execution

        Raises:
            Exception: If the retrieval fails

        """
        return await self.get_message_execution_async(
            message_id=self._assistant_message_id
        )

    def update_assistant_message_execution(
        self,
        *,
        status: MessageExecutionUpdateStatus | None = None,
        seconds_remaining: int | None = None,
        percentage_completed: int | None = None,
    ) -> MessageExecution:
        """Updates the message execution for the current assistant message synchronously.

        This is a convenience method that uses the current assistant message ID.

        Args:
            status (MessageExecutionUpdateStatus | None): The updated status (COMPLETED or FAILED). Defaults to None
            seconds_remaining (int | None): Updated estimated seconds remaining
            percentage_completed (int | None): Updated percentage of completion (0-100)

        Returns:
            MessageExecution: The updated message execution

        Raises:
            Exception: If the update fails

        """
        return self.update_message_execution(
            message_id=self._assistant_message_id,
            status=status,
            seconds_remaining=seconds_remaining,
            percentage_completed=percentage_completed,
        )

    async def update_assistant_message_execution_async(
        self,
        *,
        status: MessageExecutionUpdateStatus | None = None,
        seconds_remaining: int | None = None,
        percentage_completed: int | None = None,
    ) -> MessageExecution:
        """Updates the message execution for the current assistant message asynchronously.

        This is a convenience method that uses the current assistant message ID.

        Args:
            status (MessageExecutionUpdateStatus | None): The updated status (COMPLETED or FAILED). Defaults to None
            seconds_remaining (int | None): Updated estimated seconds remaining
            percentage_completed (int | None): Updated percentage of completion (0-100)

        Returns:
            MessageExecution: The updated message execution

        Raises:
            Exception: If the update fails

        """
        return await self.update_message_execution_async(
            message_id=self._assistant_message_id,
            status=status,
            seconds_remaining=seconds_remaining,
            percentage_completed=percentage_completed,
        )

    # Language Model Methods
    ############################################################################

    @deprecated("Use complete_with_references instead")
    def stream_complete(
        self,
        messages: LanguageModelMessages | list[ChatCompletionMessageParam],
        model_name: LanguageModelName | str,
        content_chunks: list[ContentChunk] | None = None,
        debug_info: dict = {},
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: Sequence[LanguageModelTool | LanguageModelToolDescription] | None = None,
        start_text: str | None = None,
        tool_choice: ChatCompletionToolChoiceOptionParam | None = None,
        other_options: dict | None = None,
    ) -> LanguageModelStreamResponse:
        return self.complete_with_references(
            messages=messages,
            model_name=model_name,
            content_chunks=content_chunks,
            debug_info=debug_info,
            temperature=temperature,
            timeout=timeout,
            tools=tools,
            start_text=start_text,
            tool_choice=tool_choice,
            other_options=other_options,
        )

    def complete_with_references(
        self,
        messages: LanguageModelMessages | list[ChatCompletionMessageParam],
        model_name: LanguageModelName | str,
        content_chunks: list[ContentChunk] | None = None,
        debug_info: dict | None = None,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: Sequence[LanguageModelTool | LanguageModelToolDescription] | None = None,
        start_text: str | None = None,
        tool_choice: ChatCompletionToolChoiceOptionParam | None = None,
        other_options: dict | None = None,
    ) -> LanguageModelStreamResponse:
        """Streams a completion in the chat session synchronously."""
        return stream_complete_with_references(
            company_id=self._company_id,
            user_id=self._user_id,
            assistant_message_id=self._assistant_message_id,
            user_message_id=self._user_message_id,
            chat_id=self._chat_id,
            assistant_id=self._assistant_id,
            messages=messages,
            model_name=model_name,
            content_chunks=content_chunks,
            debug_info=debug_info,
            temperature=temperature,
            timeout=timeout,
            tools=tools,
            start_text=start_text,
            tool_choice=tool_choice,
            other_options=other_options,
        )

    def complete(
        self,
        messages: LanguageModelMessages | list[ChatCompletionMessageParam],
        model_name: LanguageModelName | str,
        content_chunks: list[ContentChunk] | None = None,
        debug_info: dict | None = None,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: Sequence[LanguageModelTool | LanguageModelToolDescription] | None = None,
        start_text: str | None = None,
        tool_choice: ChatCompletionToolChoiceOptionParam | None = None,
        other_options: dict | None = None,
    ) -> LanguageModelResponse:
        response = self.complete_with_references(
            messages=messages,
            model_name=model_name,
            content_chunks=content_chunks,
            debug_info=debug_info,
            temperature=temperature,
            timeout=timeout,
            tools=tools,
            start_text=start_text,
            tool_choice=tool_choice,
            other_options=other_options,
        )

        return LanguageModelResponse.from_stream_response(response)

    @deprecated("use complete_with_references_async instead.")
    async def stream_complete_async(
        self,
        messages: LanguageModelMessages | list[ChatCompletionMessageParam],
        model_name: LanguageModelName | str,
        content_chunks: list[ContentChunk] | None = None,
        debug_info: dict | None = None,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: Sequence[LanguageModelTool | LanguageModelToolDescription] | None = None,
        start_text: str | None = None,
        tool_choice: ChatCompletionToolChoiceOptionParam | None = None,
        other_options: dict | None = None,
    ) -> LanguageModelStreamResponse:
        """Stream a completion in the chat session asynchronously."""
        return await self.complete_with_references_async(
            messages=messages,
            model_name=model_name,
            content_chunks=content_chunks,
            debug_info=debug_info,
            temperature=temperature,
            timeout=timeout,
            tools=tools,
            start_text=start_text,
            tool_choice=tool_choice,
            other_options=other_options,
        )

    async def complete_with_references_async(
        self,
        messages: LanguageModelMessages | list[ChatCompletionMessageParam],
        model_name: LanguageModelName | str,
        content_chunks: list[ContentChunk] | None = None,
        debug_info: dict | None = None,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: Sequence[LanguageModelTool | LanguageModelToolDescription] | None = None,
        tool_choice: ChatCompletionToolChoiceOptionParam | None = None,
        start_text: str | None = None,
        other_options: dict | None = None,
    ) -> LanguageModelStreamResponse:
        return await stream_complete_with_references_async(
            company_id=self._company_id,
            user_id=self._user_id,
            assistant_message_id=self._assistant_message_id,
            user_message_id=self._user_message_id,
            chat_id=self._chat_id,
            assistant_id=self._assistant_id,
            messages=messages,
            model_name=model_name,
            content_chunks=content_chunks,
            debug_info=debug_info,
            temperature=temperature,
            timeout=timeout,
            tools=tools,
            start_text=start_text,
            tool_choice=tool_choice,
            other_options=other_options,
        )

    async def complete_async(
        self,
        messages: LanguageModelMessages | list[ChatCompletionMessageParam],
        model_name: LanguageModelName | str,
        content_chunks: list[ContentChunk] | None,
        debug_info: dict | None = None,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        timeout: int = DEFAULT_COMPLETE_TIMEOUT,
        tools: Sequence[LanguageModelTool | LanguageModelToolDescription] | None = None,
        start_text: str | None = None,
        tool_choice: ChatCompletionToolChoiceOptionParam | None = None,
        other_options: dict | None = None,
    ) -> LanguageModelResponse:
        response = self.complete_with_references_async(
            messages=messages,
            model_name=model_name,
            content_chunks=content_chunks,
            debug_info=debug_info,
            temperature=temperature,
            timeout=timeout,
            tools=tools,
            start_text=start_text,
            tool_choice=tool_choice,
            other_options=other_options,
        )

        return LanguageModelResponse.from_stream_response(await response)

    def complete_responses_with_references(
        self,
        *,
        model_name: LanguageModelName | str,
        messages: str
        | LanguageModelMessages
        | Sequence[
            ResponseInputItemParam
            | LanguageModelMessageOptions
            | ResponseOutputItem  # History is automatically convertible
        ],
        content_chunks: list[ContentChunk] | None = None,
        tools: Sequence[LanguageModelToolDescription | ToolParam] | None = None,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        debug_info: dict | None = None,
        start_text: str | None = None,
        include: list[ResponseIncludable] | None = None,
        instructions: str | None = None,
        max_output_tokens: int | None = None,
        metadata: Metadata | None = None,
        parallel_tool_calls: bool | None = None,
        text: ResponseTextConfigParam | None = None,
        tool_choice: response_create_params.ToolChoice | None = None,
        top_p: float | None = None,
        reasoning: Reasoning | None = None,
        other_options: dict | None = None,
    ) -> ResponsesLanguageModelStreamResponse:
        return stream_responses_with_references(
            company_id=self._company_id,
            user_id=self._user_id,
            assistant_message_id=self._assistant_message_id,
            user_message_id=self._user_message_id,
            chat_id=self._chat_id,
            assistant_id=self._assistant_id,
            model_name=model_name,
            messages=messages,
            content_chunks=content_chunks,
            tools=tools,
            temperature=temperature,
            debug_info=debug_info,
            start_text=start_text,
            include=include,
            instructions=instructions,
            max_output_tokens=max_output_tokens,
            metadata=metadata,
            parallel_tool_calls=parallel_tool_calls,
            text=text,
            tool_choice=tool_choice,
            top_p=top_p,
            reasoning=reasoning,
            other_options=other_options,
        )

    async def complete_responses_with_references_async(
        self,
        *,
        model_name: LanguageModelName | str,
        messages: str
        | LanguageModelMessages
        | Sequence[
            ResponseInputItemParam | LanguageModelMessageOptions | ResponseOutputItem
        ],
        content_chunks: list[ContentChunk] | None = None,
        tools: Sequence[LanguageModelToolDescription | ToolParam] | None = None,
        temperature: float = DEFAULT_COMPLETE_TEMPERATURE,
        debug_info: dict | None = None,
        start_text: str | None = None,
        include: list[ResponseIncludable] | None = None,
        instructions: str | None = None,
        max_output_tokens: int | None = None,
        metadata: Metadata | None = None,
        parallel_tool_calls: bool | None = None,
        text: ResponseTextConfigParam | None = None,
        tool_choice: response_create_params.ToolChoice | None = None,
        top_p: float | None = None,
        reasoning: Reasoning | None = None,
        other_options: dict | None = None,
    ) -> ResponsesLanguageModelStreamResponse:
        return await stream_responses_with_references_async(
            company_id=self._company_id,
            user_id=self._user_id,
            assistant_message_id=self._assistant_message_id,
            user_message_id=self._user_message_id,
            chat_id=self._chat_id,
            assistant_id=self._assistant_id,
            model_name=model_name,
            messages=messages,
            content_chunks=content_chunks,
            tools=tools,
            temperature=temperature,
            debug_info=debug_info,
            start_text=start_text,
            include=include,
            instructions=instructions,
            max_output_tokens=max_output_tokens,
            metadata=metadata,
            parallel_tool_calls=parallel_tool_calls,
            text=text,
            tool_choice=tool_choice,
            top_p=top_p,
            reasoning=reasoning,
            other_options=other_options,
        )

    # Chat Content Methods
    ############################################################################

    def upload_to_chat_from_bytes(
        self,
        *,
        content: bytes,
        content_name: str,
        mime_type: str,
        scope_id: str | None = None,
        skip_ingestion: bool = False,
        hide_in_chat: bool = False,
        ingestion_config: unique_sdk.Content.IngestionConfig | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Content:
        return upload_content_from_bytes(
            user_id=self._user_id,
            company_id=self._company_id,
            content=content,
            content_name=content_name,
            mime_type=mime_type,
            scope_id=scope_id,
            chat_id=self._chat_id,
            skip_ingestion=skip_ingestion,
            hide_in_chat=hide_in_chat,
            ingestion_config=ingestion_config,
            metadata=metadata,
        )

    async def upload_to_chat_from_bytes_async(
        self,
        *,
        content: bytes,
        content_name: str,
        mime_type: str,
        scope_id: str | None = None,
        skip_ingestion: bool = False,
        hide_in_chat: bool = False,
        ingestion_config: unique_sdk.Content.IngestionConfig | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Content:
        return await upload_content_from_bytes_async(
            user_id=self._user_id,
            company_id=self._company_id,
            content=content,
            content_name=content_name,
            mime_type=mime_type,
            scope_id=scope_id,
            chat_id=self._chat_id,
            skip_ingestion=skip_ingestion,
            hide_in_chat=hide_in_chat,
            ingestion_config=ingestion_config,
            metadata=metadata,
        )

    def download_chat_content_to_bytes(self, *, content_id: str) -> bytes:
        return download_content_to_bytes(
            user_id=self._user_id,
            company_id=self._company_id,
            content_id=content_id,
            chat_id=self._chat_id,
        )

    def download_chat_images_and_documents(self) -> tuple[list[Content], list[Content]]:
        images: list[Content] = []
        files: list[Content] = []
        for c in search_contents(
            user_id=self._user_id,
            company_id=self._company_id,
            chat_id=self._chat_id,
            where={"ownerId": {"equals": self._chat_id}},
        ):
            if is_file_content(filename=c.key):
                files.append(c)
            if is_image_content(filename=c.key):
                images.append(c)
        return images, files

    # Short Term Memories
    ############################################################################

    def create_chat_memory_by_id(
        self, *, chat_id: str, key: str, value: str | dict | BaseModel
    ) -> ShortTermMemory:
        """Creates a short-term memory for a specific chat synchronously.

        Args:
            chat_id (str): The chat ID
            key (str): The memory key
            value (str | dict | BaseModel): The memory value

        Returns:
            ShortTermMemory: The created short-term memory

        Raises:
            Exception: If the creation fails
        """
        # Convert BaseModel to JSON string if needed
        if isinstance(value, BaseModel):
            value = value.model_dump_json()

        return create_memory(
            user_id=self._user_id,
            company_id=self._company_id,
            key=key,
            value=value,
            chat_id=chat_id,
        )

    async def create_chat_memory_by_id_async(
        self, *, chat_id: str, key: str, value: str | dict | BaseModel
    ) -> ShortTermMemory:
        """Creates a short-term memory for a specific chat asynchronously.

        Args:
            chat_id (str): The chat ID
            key (str): The memory key
            value (str | dict | BaseModel): The memory value

        Returns:
            ShortTermMemory: The created short-term memory

        Raises:
            Exception: If the creation fails
        """
        # Convert BaseModel to JSON string if needed
        if isinstance(value, BaseModel):
            value = value.model_dump_json()

        return await create_memory_async(
            user_id=self._user_id,
            company_id=self._company_id,
            key=key,
            value=value,
            chat_id=chat_id,
        )

    def create_message_memory_by_id(
        self, *, message_id: str, key: str, value: str | dict | BaseModel
    ) -> ShortTermMemory:
        """Creates a short-term memory for a specific message synchronously.

        Args:
            message_id (str): The message ID
            key (str): The memory key
            value (str | dict | BaseModel): The memory value

        Returns:
            ShortTermMemory: The created short-term memory

        Raises:
            Exception: If the creation fails
        """
        # Convert BaseModel to JSON string if needed
        if isinstance(value, BaseModel):
            value = value.model_dump_json()

        return create_memory(
            user_id=self._user_id,
            company_id=self._company_id,
            key=key,
            value=value,
            message_id=message_id,
        )

    async def create_message_memory_by_id_async(
        self, *, message_id: str, key: str, value: str | dict | BaseModel
    ) -> ShortTermMemory:
        """Creates a short-term memory for a specific message asynchronously.

        Args:
            message_id (str): The message ID
            key (str): The memory key
            value (str | dict | BaseModel): The memory value

        Returns:
            ShortTermMemory: The created short-term memory

        Raises:
            Exception: If the creation fails
        """
        # Convert BaseModel to JSON string if needed
        if isinstance(value, BaseModel):
            value = value.model_dump_json()

        return await create_memory_async(
            user_id=self._user_id,
            company_id=self._company_id,
            key=key,
            value=value,
            message_id=message_id,
        )

    def find_chat_memory_by_id(self, *, chat_id: str, key: str) -> ShortTermMemory:
        """Finds the latest short-term memory for a specific chat synchronously.

        Args:
            chat_id (str): The chat ID
            key (str): The memory key

        Returns:
            ShortTermMemory: The latest short-term memory

        Raises:
            Exception: If the retrieval fails
        """
        return find_latest_memory(
            user_id=self._user_id,
            company_id=self._company_id,
            key=key,
            chat_id=chat_id,
        )

    async def find_chat_memory_by_id_async(
        self, *, chat_id: str, key: str
    ) -> ShortTermMemory:
        """Finds the latest short-term memory for a specific chat asynchronously.

        Args:
            chat_id (str): The chat ID
            key (str): The memory key

        Returns:
            ShortTermMemory: The latest short-term memory

        Raises:
            Exception: If the retrieval fails
        """
        return await find_latest_memory_async(
            user_id=self._user_id,
            company_id=self._company_id,
            key=key,
            chat_id=chat_id,
        )

    def find_message_memory_by_id(
        self, *, message_id: str, key: str
    ) -> ShortTermMemory:
        """Finds the latest short-term memory for a specific message synchronously.

        Args:
            message_id (str): The message ID
            key (str): The memory key

        Returns:
            ShortTermMemory: The latest short-term memory

        Raises:
            Exception: If the retrieval fails
        """
        return find_latest_memory(
            user_id=self._user_id,
            company_id=self._company_id,
            key=key,
            message_id=message_id,
        )

    async def find_message_memory_by_id_async(
        self, *, message_id: str, key: str
    ) -> ShortTermMemory:
        """Finds the latest short-term memory for a specific message asynchronously.

        Args:
            message_id (str): The message ID
            key (str): The memory key

        Returns:
            ShortTermMemory: The latest short-term memory

        Raises:
            Exception: If the retrieval fails
        """
        return await find_latest_memory_async(
            user_id=self._user_id,
            company_id=self._company_id,
            key=key,
            message_id=message_id,
        )

    # Convenience methods using current chat/message IDs
    ############################################################################

    def create_chat_memory(
        self, *, key: str, value: str | dict | BaseModel
    ) -> ShortTermMemory:
        """Creates a short-term memory for the current chat synchronously.

        Args:
            key (str): The memory key
            value (str | dict | BaseModel): The memory value

        Returns:
            ShortTermMemory: The created short-term memory

        Raises:
            Exception: If the creation fails
        """
        return self.create_chat_memory_by_id(
            chat_id=self._chat_id,
            key=key,
            value=value,
        )

    async def create_chat_memory_async(
        self, *, key: str, value: str | dict | BaseModel
    ) -> ShortTermMemory:
        """Creates a short-term memory for the current chat asynchronously.

        Args:
            key (str): The memory key
            value (str | dict | BaseModel): The memory value

        Returns:
            ShortTermMemory: The created short-term memory

        Raises:
            Exception: If the creation fails
        """
        return await self.create_chat_memory_by_id_async(
            chat_id=self._chat_id,
            key=key,
            value=value,
        )

    @overload
    def create_message_memory(
        self,
        *,
        key: str,
        value: str | dict | BaseModel,
    ) -> ShortTermMemory: ...

    @overload
    def create_message_memory(
        self, *, key: str, value: str | dict | BaseModel, message_id: str
    ) -> ShortTermMemory: ...

    def create_message_memory(
        self, *, key: str, value: str | dict | BaseModel, message_id: str | None = None
    ) -> ShortTermMemory:
        """Creates a short-term memory for the current assistant message synchronously.

        Args:
            key (str): The memory key
            value (str | dict | BaseModel): The memory value

        Returns:
            ShortTermMemory: The created short-term memory

        Raises:
            Exception: If the creation fails
        """
        return self.create_message_memory_by_id(
            key=key,
            value=value,
            message_id=message_id or self._assistant_message_id,
        )

    @overload
    async def create_message_memory_async(
        self,
        *,
        key: str,
        value: str | dict | BaseModel,
    ) -> ShortTermMemory: ...

    @overload
    async def create_message_memory_async(
        self, *, key: str, value: str | dict | BaseModel, message_id: str
    ) -> ShortTermMemory: ...

    async def create_message_memory_async(
        self, *, key: str, value: str | dict | BaseModel, message_id: str | None = None
    ) -> ShortTermMemory:
        """Creates a short-term memory for the current assistant message asynchronously.

        Args:
            key (str): The memory key
            value (str | dict | BaseModel): The memory value

        Returns:
            ShortTermMemory: The created short-term memory

        Raises:
            Exception: If the creation fails
        """
        return await self.create_message_memory_by_id_async(
            message_id=message_id or self._assistant_message_id,
            key=key,
            value=value,
        )

    def find_chat_memory(self, *, key: str) -> ShortTermMemory:
        """Finds the latest short-term memory for the current chat synchronously.

        Args:
            key (str): The memory key

        Returns:
            ShortTermMemory: The latest short-term memory

        Raises:
            Exception: If the retrieval fails
        """
        return self.find_chat_memory_by_id(
            chat_id=self._chat_id,
            key=key,
        )

    async def find_chat_memory_async(self, *, key: str) -> ShortTermMemory:
        """Finds the latest short-term memory for the current chat asynchronously.

        Args:
            key (str): The memory key

        Returns:
            ShortTermMemory: The latest short-term memory

        Raises:
            Exception: If the retrieval fails
        """
        return await self.find_chat_memory_by_id_async(
            chat_id=self._chat_id,
            key=key,
        )

    @overload
    def find_message_memory(self, *, key: str) -> ShortTermMemory: ...

    @overload
    def find_message_memory(self, *, key: str, message_id: str) -> ShortTermMemory: ...

    def find_message_memory(
        self, *, key: str, message_id: str | None = None
    ) -> ShortTermMemory:
        """Finds the latest short-term memory for the current assistant message synchronously.

        Args:
            key (str): The memory key

        Returns:
            ShortTermMemory: The latest short-term memory

        Raises:
            Exception: If the retrieval fails
        """
        return self.find_message_memory_by_id(
            message_id=message_id or self._assistant_message_id,
            key=key,
        )

    @overload
    async def find_message_memory_async(self, *, key: str) -> ShortTermMemory: ...

    @overload
    async def find_message_memory_async(
        self, *, key: str, message_id: str
    ) -> ShortTermMemory: ...

    async def find_message_memory_async(
        self, *, key: str, message_id: str | None = None
    ) -> ShortTermMemory:
        """Finds the latest short-term memory for the current assistant message asynchronously.

        Args:
            key (str): The memory key

        Returns:
            ShortTermMemory: The latest short-term memory

        Raises:
            Exception: If the retrieval fails
        """
        return await self.find_message_memory_by_id_async(
            message_id=message_id or self._assistant_message_id,
            key=key,
        )
