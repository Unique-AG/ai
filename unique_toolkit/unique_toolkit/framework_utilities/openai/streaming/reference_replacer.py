"""Reference resolution as a ``StreamingReplacerProtocol`` implementation.

``ReferenceResolutionReplacer`` accumulates the full normalised ``[N]`` text produced
by upstream ``StreamingPatternReplacer`` instances and converts it to ``<sup>N</sup>``
footnotes at flush time, so reference resolution is part of the replacer pipeline
rather than a separate post-stream step in the handler.

The persistence layer's ``on_stream_end`` must use a *cascade flush* (see
``responses_sdk_persistence`` / ``chat_completion_sdk_persistence``) so that the
pattern replacer's buffered tail is fed into this replacer's ``process()`` before
``flush()`` is called.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from unique_toolkit.framework_utilities.openai.streaming.pattern_replacer import (
    StreamingReplacerProtocol,
)

if TYPE_CHECKING:
    from unique_toolkit.content.schemas import ContentChunk, ContentReference


class ReferenceResolutionReplacer(StreamingReplacerProtocol):
    """Converts ``[N]`` bracket references to ``<sup>N</sup>`` footnotes at flush time.

    Place this replacer **after** any ``StreamingPatternReplacer`` in the chain so it
    receives already-normalised ``[N]`` text.  During streaming, text passes through
    unchanged (providing live preview in ``[N]`` format).  At flush time the replacer
    runs the full reference resolution pipeline on the accumulated text and stores the
    result; the handler can then read :attr:`resolved_text` and :attr:`references`.

    Args:
        content_chunks: The search results used to build the model context.  Index
            ``N - 1`` in this list corresponds to ``[N]`` in the model output.
        message_id: The ID of the assistant message being streamed.  Required by
            ``_add_references`` for building ``ContentReference`` objects.
        model: Optional model name forwarded to ``_add_references`` for
            model-specific post-processing (e.g. Gemini reference limiting).
    """

    def __init__(
        self,
        content_chunks: list[ContentChunk],
        message_id: str,
        model: str | None = None,
    ) -> None:
        self._content_chunks = content_chunks
        self._message_id = message_id
        self._model = model
        self._accumulated = ""
        self._references: list[ContentReference] = []
        self._resolved_text: str = ""

    def process(self, delta: str) -> str:
        """Accumulate *delta* and pass it through unchanged for live streaming preview."""
        self._accumulated += delta
        return delta

    def flush(self) -> str:
        """Run reference resolution on the complete accumulated text.

        Applies the three-stage pipeline:

        1. ``_preprocess_message`` — normalise any remaining ``[source N]`` variants
           to ``[N]`` (second pass, idempotent for already-normalised text).
        2. ``_add_references`` — match ``[N]`` to ``ContentChunk`` entries, build
           ``ContentReference`` objects, replace ``[N]`` with ``<sup>N</sup>``.
        3. ``_postprocess_message`` — deduplicate consecutive ``<sup>`` runs.

        The result is stored in :attr:`resolved_text` and :attr:`references`.

        Returns:
            An empty string — text was already released incrementally by
            :meth:`process`.  The caller should read :attr:`resolved_text` to obtain
            the fully resolved text and update the message object accordingly.
        """
        if not self._accumulated:
            return ""

        from unique_toolkit.language_model.reference import (
            _add_references,
            _postprocess_message,
            _preprocess_message,
        )

        text = _preprocess_message(self._accumulated)
        text, self._references = _add_references(
            text,
            self._content_chunks,
            self._message_id,
            self._model,
        )
        self._resolved_text = _postprocess_message(text)
        return ""

    @property
    def resolved_text(self) -> str:
        """Fully resolved text with ``<sup>N</sup>`` footnotes (available after flush)."""
        return self._resolved_text

    @property
    def references(self) -> list[ContentReference]:
        """``ContentReference`` objects matched during resolution (available after flush)."""
        return list(self._references)
