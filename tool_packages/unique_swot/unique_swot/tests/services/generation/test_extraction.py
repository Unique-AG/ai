from types import SimpleNamespace

from unique_swot.services.generation.extraction.agent import _split_context_into_batches
from unique_swot.services.source_management.schema import (
    Source,
    SourceChunk,
    SourceType,
)


class _DummyEncoding:
    def encode(self, text: str):
        return [0] * len(text)


def _llm():
    return SimpleNamespace(encoder_name="dummy")


def test_split_context_respects_token_limit(monkeypatch):
    monkeypatch.setattr(
        "unique_swot.services.generation.extraction.agent.get_encoding",
        lambda _: _DummyEncoding(),
    )

    source = Source(
        type=SourceType.WEB,
        url="http://example.com",
        title="example",
        chunks=[
            SourceChunk(id="c1", text="a" * 10),
            SourceChunk(id="c2", text="b" * 15),
            SourceChunk(id="c3", text="c" * 5),
        ],
    )

    batches = _split_context_into_batches(
        source=source,
        batch_size=2,
        max_tokens_per_batch=20,
        llm=_llm(),
    )

    assert len(batches.batches) == 2
    assert [chunk.id for chunk in batches.batches[0]] == ["c1"]
    assert [chunk.id for chunk in batches.batches[1]] == ["c2", "c3"]


def test_split_context_respects_batch_size(monkeypatch):
    monkeypatch.setattr(
        "unique_swot.services.generation.extraction.agent.get_encoding",
        lambda _: _DummyEncoding(),
    )

    source = Source(
        type=SourceType.WEB,
        url=None,
        title="example",
        chunks=[SourceChunk(id=f"c{i}", text="x" * 2) for i in range(3)],
    )

    batches = _split_context_into_batches(
        source=source,
        batch_size=1,
        max_tokens_per_batch=100,
        llm=_llm(),
    )

    assert len(batches.batches) == 3
    assert [chunk.id for chunk in batches.batches[0]] == ["c0"]
    assert [chunk.id for chunk in batches.batches[1]] == ["c1"]
    assert [chunk.id for chunk in batches.batches[2]] == ["c2"]
