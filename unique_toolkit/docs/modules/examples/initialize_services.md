## Initialization
The services of the unique toolkit can be used to 

- manage and query with the knowledgebase
- interact with the chat frontend
- use language and embedding models


## Initialization in standalone setting

To interact with the we need to know the `user_id` and `company_id` which we set in the `.env` file here as it is typically done in [standalone applications](./../../../standalone_application.md).

``` {.python #init_content_service_from_ids}
content_service = ContentService(
    company_id=settings.auth.company_id.get_secret_value(),
    user_id=settings.auth.user_id.get_secret_value(),
)
```


``` {.python #initialize_content_service_standalone}
from pathlib import Path
from unique_toolkit.app.init_sdk import init_unique_sdk
from unique_toolkit import ContentService, LanguageModelService, EmbeddingService
from unique_toolkit.app.unique_settings import UniqueSettings

settings = UniqueSettings.from_env(env_file=Path("../.env"))
init_unique_sdk(unique_settings=settings)


llm_service = LanguageModelService(
    company_id=settings.auth.company_id.get_secret_value(),
    user_id=settings.auth.user_id.get_secret_value(),
)

embedding_service = EmbeddingService(
    company_id=settings.auth.company_id.get_secret_value(),
    user_id=settings.auth.user_id.get_secret_value(),
)

# Your application logic here
```

## Initialization in the event driven setting
When working in a [event driven setting](../../../event_driven_applications.md) the services can be initialized directly from the event and is usually instantiated freshly for every request to ensure statelessness. In the development setup the connection to the unique plattform can be achieved through an SSE client. 
``` {.python #obtaining_sse_client file=examples/generated/init_services_via_sse_client.py}
from unique_toolkit.app.sse_client import get_sse_client 
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.app.init_sdk import init_unique_sdk
from pathlib import Path
from unique_toolkit.app.schemas import EventName
from unique_toolkit.app.event_util import load_and_filter_event
from typing import Any

from examples.generated.content_event_driven import instantiate_services_from_event

def main():
    settings = UniqueSettings.from_env(env_file=Path("../.env"))
    init_unique_sdk(unique_settings=settings)

    sse_client = get_sse_client(unique_settings=settings, 
                                subscriptions=[EventName.EXTERNAL_MODULE_CHOSEN])

    for request in sse_client:
        try:
            chat_event = load_and_filter_event(request, 
                                               EventName.EXTERNAL_MODULE_CHOSEN)
        except Exception:
            return 500

        if chat_event:

            content_service, chat_service, llm_service, embedding_service = instantiate_services_from_event(chat_event)

            # your application logic here

            return 200
```

<!--
``` {.python #import_all_services}
from unique_toolkit import (
    ContentService,
    ChatService,
    LanguageModelService,
    EmbeddingService,
)
```
-->

<!--
``` {.python #instantiate_all_services_from_event}
from unique_toolkit.app.schemas import ChatEvent

def instantiate_services_from_event(
    event: ChatEvent,
) -> tuple[ContentService, ChatService, LanguageModelService, EmbeddingService]:
    content_service = ContentService.from_event(event)
    chat_service = ChatService(event)
    llm_service = LanguageModelService.from_event(event)
    embedding_service = EmbeddingService.from_event(event)
    return content_service, chat_service, llm_service, embedding_service
```
-->

