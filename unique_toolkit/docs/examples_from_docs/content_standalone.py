# %%
# ~/~ begin <<docs/modules/examples/content/content_service.md#docs/.python_files/content_standalone.py>>[init]
# %%
# ~/~ begin <<docs/application_types/standalone_application.md#initialize_content_service_standalone>>[init]
from pathlib import Path

from unique_toolkit import ContentService, EmbeddingService, LanguageModelService
from unique_toolkit.app.init_sdk import init_unique_sdk
from unique_toolkit.app.unique_settings import UniqueSettings

settings = UniqueSettings.from_env(env_file=Path("../.env"))

init_unique_sdk(unique_settings=settings)

content_service = ContentService.from_settings(settings=settings)
llm_service = LanguageModelService.from_settings(settings=settings)
embedding_service = EmbeddingService.from_settings(settings=settings)

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
