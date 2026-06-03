from unique_search_proxy.web.core.crawlers.basic.processing.errors import (
    ContentProcessingError,
)


async def process_pdf(body: str, *, timeout: float) -> str:
    del body, timeout
    raise ContentProcessingError(
        "PDF processing is not implemented for the basic crawler yet",
    )
