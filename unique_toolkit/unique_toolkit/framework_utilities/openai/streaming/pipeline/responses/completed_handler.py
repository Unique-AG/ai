"""Handler for ``ResponseCompletedEvent`` — extracts usage and output."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai.types.responses import ResponseCompletedEvent, ResponseOutputItem

from unique_toolkit.language_model.schemas import LanguageModelTokenUsage


class ResponsesCompletedHandler:
    """Extracts ``LanguageModelTokenUsage`` and ``output`` from ``ResponseCompletedEvent``.

    Private state: ``_usage``, ``_output``.
    """

    def __init__(self) -> None:
        self._usage: LanguageModelTokenUsage | None = None
        self._output: list[ResponseOutputItem] = []

    async def on_completed(self, event: ResponseCompletedEvent) -> None:
        self._usage = _extract_usage(event)
        if event.response.output is not None:
            self._output = list(event.response.output)

    def get_usage(self) -> LanguageModelTokenUsage | None:
        return self._usage

    def get_output(self) -> list[ResponseOutputItem]:
        return list(self._output)

    async def on_stream_end(self) -> None:
        pass

    def reset(self) -> None:
        self._usage = None
        self._output = []


def _extract_usage(event: ResponseCompletedEvent) -> LanguageModelTokenUsage | None:
    usage = event.response.usage
    if usage is None:
        return None
    return LanguageModelTokenUsage(
        prompt_tokens=usage.input_tokens,
        completion_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
    )
