from unique_swot.services.schemas import Source


def batch_parser(batch: list[Source]) -> str:
    return "\n".join([source.content for source in batch])
