# %%
# ~/~ begin <<docs/modules/examples/content/content_service.md#docs/.python_files/content_standalone.py>>[init]
# %%
# ~/~ begin <<docs/application_types/standalone_application.md#initialize_content_service_standalone>>[init]

from unique_toolkit import ContentService, EmbeddingService, LanguageModelService
from unique_toolkit.content.schemas import ContentSearchType

content_service = ContentService.from_settings()
llm_service = LanguageModelService.from_settings()
embedding_service = EmbeddingService.from_settings()

# Your application logic here
# ~/~ end
# ~/~ begin <<docs/modules/examples/content/content_service.md#content_service_search_content_chunks>>[init]
content_chunks = content_service.search_content_chunks(
    search_string="Hello, world!",
    search_type=ContentSearchType.VECTOR,
    limit=10,
)
# ~/~ end
# ~/~ end
