# Development Setup with Server Sent Events (SSE)
The following secrets must be configured for this in an `unique.env` file or in the environment when developing with SSE

```env
UNIQUE_API_BASE_URL=            # The backend url of Unique's public API
UNIQUE_API_VERSION=             # The version Unique's public API

UNIQUE_APP_ID=                  # The app id as obtained in the App secion of Unique
UNIQUE_APP_KEY=                 # The app key as obtained in the App secion of Unique

UNIQUE_AUTH_COMPANY_ID=
UNIQUE_AUTH_USER_ID=
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
    <<init_services_from_event>>

```
??? example "Full Examples (Click to expand)"
    
    <!--codeinclude-->
    [Full SSE Setup](../examples_from_docs/sse_setup_with_services.py)
    <!--/codeinclude-->

