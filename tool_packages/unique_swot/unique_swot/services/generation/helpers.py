from unique_swot.services.collection.schema import SourceChunk

CHUNK_TEMPLATE = """
<chunk id="{id}">
{text}
</chunk id="{id}">
"""


def batch_parser(batch: list[SourceChunk]) -> str:
    return "\n".join(
        CHUNK_TEMPLATE.format(id=chunk.id, text=chunk.text) for chunk in batch
    )
