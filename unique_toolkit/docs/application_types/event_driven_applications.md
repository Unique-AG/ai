# Event Driven App

A event driven application reacts to events obtained from the Unique plattfom. These event can be used to initialize services that in turn have effect on the chat, knowledge base or the magic table.

## Obtaining Events

How events are obtained depends on how the appliction is being run. Important is that successive events should not have any effect onto each other, thus ideally your functionality is stateless and all necessary state is obtained via the services of the Unique Plattform.

### Development

In a development setup events can be obtained via a Server Sent Events (SSE) Client. The following secrets must be configured for this in an `.env` file or in the environment

```env
UNIQUE_API_BASE_URL=            # The backend url of Unique's public API
UNIQUE_API_VERSION=             # The version Unique's public API

UNIQUE_APP_ID=                  # The app id as obtained in the App secion of Unique
UNIQUE_APP_KEY=                 # The app key as obtained in the App secion of Unique
```

For convenience we provide the `get_event_generator` functionality that hides the complexities of the SSE client such that it suffices to specify the type of event the application is looking for. At the moment only `ChatEvent` is available but other events will soon follow.


<!--
```{.python #unique_settings_import}
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.app.init_sdk import init_unique_sdk
```

``` {.python #unique_sse_setup_import}
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent 
```
-->
```{.python #unique_setup_settings_sdk_from_env}
settings = UniqueSettings.from_env_auto_with_sdk_init()
```

```{.python #obtaining_sse_client_with_chat_event}
for event in get_event_generator(unique_settings=settings, event_type=ChatEvent):
    chat_service = ChatService(event)
```

## Service Initialization from Events

Once you have an event, you can initialize services directly from it:

```python
# Initialize services from event
chat_service = ChatService(event)
content_service = ContentService.from_event(event)

```
<!--
```{.python #full_sse_setup file=docs/.python_files/sse_setup.py}
<<common_imports>>
<<unique_setup_settings_sdk_from_env>>
<<obtaining_sse_client_with_chat_event>>
```
-->


??? example "Full Examples (Click to expand)"
    
    <!--codeinclude-->
    [Full SSE Setup](../examples_from_docs/sse_setup.py)
    <!--/codeinclude-->



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

