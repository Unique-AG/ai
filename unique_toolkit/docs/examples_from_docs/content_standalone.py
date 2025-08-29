# %%

from unique_toolkit import ContentService, EmbeddingService, LanguageModelService
from unique_toolkit.content.schemas import ContentSearchType

content_service = ContentService.from_settings()
llm_service = LanguageModelService.from_settings()
embedding_service = EmbeddingService.from_settings()

content_chunks = content_service.search_content_chunks(
    search_string="Hello, world!",
    search_type=ContentSearchType.VECTOR,
    limit=10,
)

# %%
