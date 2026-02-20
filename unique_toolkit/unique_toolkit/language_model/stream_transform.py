import copy
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from unique_toolkit.chat.schemas import ChatMessage, ChatMessageRole
from unique_toolkit.content.schemas import ContentChunk, ContentReference
from unique_toolkit.language_model.reference import add_references_to_message


@runtime_checkable
class StreamTransform(Protocol):
    def process_delta(self, delta: str) -> None: ...

    def finalize(self, text: str) -> tuple[str, list[ContentReference]]: ...


class ReferenceInjectionTransform:
    """Transform to inject references into the text of a message."""

    def __init__(self, content_chunks: list[ContentChunk], model: str | None = None):
        self._content_chunks = content_chunks
        self._model = (
            model  # needed e.g. for gemini-2.5 models to limit the number of references
        )

    def process_delta(self, delta: str) -> None:
        pass  # cannot manipulate delta right now, as it is a stream

    def finalize(self, text: str) -> tuple[str, list[ContentReference]]:
        message = ChatMessage(
            id="irrelevant",
            text=copy.deepcopy(text),
            role=ChatMessageRole.ASSISTANT,
            created_at=datetime.now(UTC),
            chat_id="irrelevant",
        )

        updated_message, __ = add_references_to_message(
            message=message,
            search_context=self._content_chunks,
            model=self._model,
        )

        references: list[ContentReference] = [
            ContentReference(**u.model_dump()) for u in updated_message.references or []
        ]
        return updated_message.content or "", references


class NormalizationTransform:
    """Transform to normalize the text of a message.
    E.g. remove extra whitespace, convert to lowercase, etc.
    Placeholder for now.
    """

    def process_delta(self, delta: str) -> None:
        pass

    def finalize(self, text: str) -> tuple[str, list[ContentReference]]:
        return text.strip(), []


class TextTransformPipeline:
    """Pipeline of text transforms to be applied to a stream of text."""

    def __init__(self):
        self._transforms: list[StreamTransform] = []

    def add(self, transform: StreamTransform) -> "TextTransformPipeline":
        self._transforms.append(transform)
        return self

    def feed_delta(self, delta: str) -> None:
        for transform in self._transforms:
            transform.process_delta(delta)

    def run(self, text: str) -> tuple[str, list[ContentReference]]:
        refs_: list[ContentReference] = []
        text_: str = text
        for transform in self._transforms:
            text_, new_refs = transform.finalize(text_)
            refs_.extend(new_refs)
        return text_, refs_
