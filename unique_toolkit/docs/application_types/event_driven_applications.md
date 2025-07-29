# Event Driven Applications

A event driven application reacts to events obtained from the Unique plattfom. These event can be used to initialize services that in turn have effect on the chat, knowledge base or the magic table.

## Obtaining Events

How events are obtained depends on how the appliction being ran. Important is that successive events should not have any effect onto each other, thus ideally your functionality is stateless and all necessary state is obtained via the services of the Unique Plattform.

### Development

In a development setup events can be obtained via a Server Sent Events (SSE) Client. The following secrets must be configured for this in an `.env` file or in the environment

```env
UNIQUE_API_BASE_URL=            # The backend url of Unique's public API
UNIQUE_API_VERSION=             # The version Unique's public API

UNIQUE_APP_ID=                  # The app id as obtained in the App secion of Unique
UNIQUE_APP_KEY=                 # The app key as obtained in the App secion of Unique
```

For convenience we proved the `get_event_generator` functionality that hides the complexities of the SSE client such that it suffices to specify the type of event the application is looking for. At the moment only `ChatEvent` is available.

``` {.python #obtaining_sse_client file=examples/generated/init_services_via_sse_client.py}

from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.app.schemas import ChatEvent 
from pathlib import Path
from unique_toolkit.app.init_sdk import init_unique_sdk
from unique_toolkit import ChatService, ShortTermMemoryService

settings = UniqueSettings.from_env(env_file=Path(__file__).parent.parent.parent / ".env")
init_unique_sdk(unique_settings=settings)

for event in get_event_generator(unique_settings=settings, event_type=ChatEvent):
    chat_service = ChatService(event)
    short_term_memory_service = ShortTermMemoryService.from_event(event)
```


### Production

In a production setup the events are obtained via a WebHook. The following secrets must be configured for this in an `.env` file or in the environment


```env
UNIQUE_API_BASE_URL=            # The backend url of Unique's public API
UNIQUE_API_VERSION=             # The version Unique's public API

UNIQUE_APP_ID=                  # The app id as obtained in the App secion of Unique
UNIQUE_APP_KEY=                 # The app key as obtained in the App secion of Unique
UNIQUE_APP_ENDPOINT=            # The app endpoint where the container is reachable (**CHECK THIS**)
UNIQUE_APP_ENDPOINT_SECRET=     # The app endpoint secret (**CHECK THIS**)
```


Services can again be directly initialized from the events. 

(WORK IN PROGRESS)

