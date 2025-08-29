# ~/~ begin <<docs/application_types/standalone_application.md#standalone_setup>>[init]
from unique_toolkit import ContentService
from unique_toolkit.app.unique_settings import UniqueSettings
# ~/~ begin <<docs/plattforms/openai/openai.md#openai_toolkit_imports>>[init]
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.client import get_openai_client
from unique_toolkit.framework_utilities.openai.message_builder import (
    OpenAIMessageBuilder,
)
# ~/~ end

# ~/~ begin <<docs/application_types/standalone_application.md#unique_setup_settings_sdk_from_env_standalone>>[init]
settings = UniqueSettings.from_env_auto_with_sdk_init()
# ~/~ end
# ~/~ begin <<docs/application_types/standalone_application.md#unique_init_service_standalone>>[init]
content_service = ContentService.from_settings(settings=settings)
# ~/~ end
client = get_openai_client(unique_settings=settings)
# ~/~ end
