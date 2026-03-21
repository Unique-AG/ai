from typing import Any
from urllib.parse import quote_plus

from unique_sdk.api_resources._message import Message
from unique_sdk.api_resources._message_assessment import MessageAssessment
from unique_sdk.api_resources._message_execution import MessageExecution
from unique_sdk.api_resources._message_log import MessageLog
from unique_sdk.api_resources._message_tool import MessageTool
from unique_sdk._list_object import ListObject

from .._base import BaseManager, DomainObject


class MessageObject(DomainObject):
    """A single chat message with mutation methods."""

    async def modify(self, **params: Any) -> "MessageObject":
        """Update this message (text, references, debugInfo, timestamps, …)."""
        result = await Message.modify_async(
            self._user_id, self._company_id, self.id, **params
        )
        self._update_raw(result)
        return self

    async def delete(self, **params: Any) -> None:
        """Permanently delete this message."""
        await self._raw.delete_async(self._user_id, self._company_id, **params)

    async def create_event(self, **params: Any) -> "MessageObject":
        """Create a streaming event on this message."""
        params["messageId"] = self.id
        result = await Message.create_event_async(
            self._user_id, self._company_id, **params
        )
        return MessageObject(self._user_id, self._company_id, result)


class MessageManager(BaseManager):
    """CRUD operations for Messages."""

    async def list(self, **params: Any) -> list[MessageObject]:
        result = await Message.list_async(self._user_id, self._company_id, **params)
        return [MessageObject(self._user_id, self._company_id, m) for m in result]

    async def retrieve(self, id: str, **params: Any) -> MessageObject:
        result = await Message.retrieve_async(
            self._user_id, self._company_id, id, **params
        )
        return MessageObject(self._user_id, self._company_id, result)

    async def create(self, **params: Any) -> MessageObject:
        result = await Message.create_async(self._user_id, self._company_id, **params)
        return MessageObject(self._user_id, self._company_id, result)

    async def modify(self, id: str, **params: Any) -> MessageObject:
        result = await Message.modify_async(
            self._user_id, self._company_id, id, **params
        )
        return MessageObject(self._user_id, self._company_id, result)

    async def delete(self, id: str, **params: Any) -> None:
        url = f"{Message.class_url()}/{quote_plus(id)}"
        await Message._static_request_async(
            "delete", url, self._user_id, self._company_id, params=params
        )


# ---------------------------------------------------------------------------
# MessageLog
# ---------------------------------------------------------------------------


class MessageLogObject(DomainObject):
    """A message log entry with update capability."""

    async def update(self, **params: Any) -> "MessageLogObject":
        result = await MessageLog.update_async(
            self._user_id, self._company_id, self.id, **params
        )
        self._update_raw(result)
        return self


class MessageLogManager(BaseManager):
    async def create(self, **params: Any) -> MessageLogObject:
        result = await MessageLog.create_async(
            self._user_id, self._company_id, **params
        )
        return MessageLogObject(self._user_id, self._company_id, result)

    async def update(self, message_log_id: str, **params: Any) -> MessageLogObject:
        result = await MessageLog.update_async(
            self._user_id, self._company_id, message_log_id, **params
        )
        return MessageLogObject(self._user_id, self._company_id, result)


# ---------------------------------------------------------------------------
# MessageTool
# ---------------------------------------------------------------------------


class MessageToolObject(DomainObject):
    """A single message tool entry."""


class MessageToolManager(BaseManager):
    async def create_many(self, **params: Any) -> list[MessageToolObject]:
        result = await MessageTool.create_many_async(
            self._user_id, self._company_id, **params
        )
        return [MessageToolObject(self._user_id, self._company_id, m) for m in result]

    async def get_message_tools(self, **params: Any) -> list[MessageToolObject]:
        result = await MessageTool.get_message_tools_async(
            self._user_id, self._company_id, **params
        )
        return [MessageToolObject(self._user_id, self._company_id, m) for m in result]


# ---------------------------------------------------------------------------
# MessageAssessment
# ---------------------------------------------------------------------------


class MessageAssessmentObject(DomainObject):
    """A message assessment with modify capability."""

    async def modify(self, **params: Any) -> "MessageAssessmentObject":
        result = await MessageAssessment.modify_async(
            self._user_id, self._company_id, **params
        )
        self._update_raw(result)
        return self


class MessageAssessmentManager(BaseManager):
    async def create(self, **params: Any) -> MessageAssessmentObject:
        result = await MessageAssessment.create_async(
            self._user_id, self._company_id, **params
        )
        return MessageAssessmentObject(self._user_id, self._company_id, result)

    async def modify(self, **params: Any) -> MessageAssessmentObject:
        result = await MessageAssessment.modify_async(
            self._user_id, self._company_id, **params
        )
        return MessageAssessmentObject(self._user_id, self._company_id, result)


# ---------------------------------------------------------------------------
# MessageExecution
# ---------------------------------------------------------------------------


class MessageExecutionObject(DomainObject):
    """A long-running message execution."""

    async def update(self, **params: Any) -> "MessageExecutionObject":
        result = await MessageExecution.update_async(
            self._user_id, self._company_id, **params
        )
        self._update_raw(result)
        return self


class MessageExecutionManager(BaseManager):
    async def create(self, **params: Any) -> MessageExecutionObject:
        result = await MessageExecution.create_async(
            self._user_id, self._company_id, **params
        )
        return MessageExecutionObject(self._user_id, self._company_id, result)

    async def get(self, **params: Any) -> MessageExecutionObject:
        result = await MessageExecution.get_async(
            self._user_id, self._company_id, **params
        )
        return MessageExecutionObject(self._user_id, self._company_id, result)

    async def update(self, **params: Any) -> MessageExecutionObject:
        result = await MessageExecution.update_async(
            self._user_id, self._company_id, **params
        )
        return MessageExecutionObject(self._user_id, self._company_id, result)
