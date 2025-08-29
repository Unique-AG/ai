# %%
from unique_toolkit import (
    ContentService,
)
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.client import get_openai_client

settings = UniqueSettings.from_env_auto_with_sdk_init()
content_service = ContentService.from_settings(settings=settings)
client = get_openai_client(unique_settings=settings)
