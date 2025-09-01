# %%
from unique_toolkit import (
    ContentService,
)
from unique_toolkit.framework_utilities.openai.client import get_openai_client

content_service = ContentService.from_settings_filename()
client = get_openai_client()
