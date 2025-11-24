# Event Driven App

A event driven application reacts to events obtained from the Unique plattfom. These event can be used to initialize services that in turn have effect on the chat, knowledge base or the agentic table.

For a secure application it is paramount that successive events do not have any effect onto each other, thus ideally your functionality is stateless and all necessary state is obtained via the services of the Unique Plattform.

## Development Setup


### Using Server Sent Events (SSE)
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



### Using Webhooks and ngrok

The following secrets must be configured for this in an `unique.env` file or in the environment when developing with SSE

```env
UNIQUE_API_BASE_URL=            # The backend url of Unique's public API
UNIQUE_API_VERSION=             # The version Unique's public API

UNIQUE_APP_ID=                  # The app id as obtained in the App secion of Unique
UNIQUE_APP_KEY=                 # The app key as obtained in the App secion of Unique

UNIQUE_AUTH_COMPANY_ID=
UNIQUE_AUTH_USER_ID=

UNIQUE_APP_ENDPOINT=            # The app endpoint where the container is reachable (**CHECK THIS**)
UNIQUE_APP_ENDPOINT_SECRET=     # The app endpoint secret (**CHECK THIS**)
```


A minimal application could look like this


??? example "Example Application"
    
    <!--codeinclude-->
    [Custom Application with FastAPI](./../examples_from_docs/fastapi_app_minimal.py)
    <!--/codeinclude-->


This can be run using the debugger and will be exposed locally under `http://localhost:5001`. To make the application available to the platform we can expose it using [ngrok](https://ngrok.com/), therefore we execute 

```
ngrok http 5001
```

on the command line. This will open a live console with the following content 

```
ngrok
                                                                                                                                                                                                                         
⚠️ Free Users: Agents ≤3.18.x stop connecting 12/17/25. Update or upgrade: https://ngrok.com/pricing                                                                                                                     
                                                                                                                                                                                                                         
Session Status             online                                                                                                                                                                                     
Account                       <redacted> (Plan: Free)                                                                                                                                                                          
Update                        update available (version 3.33.0, Ctrl-U to update)                                                                                                                                        
Version                       3.25.0                                                                                                                                                                                     
Region                        Europe (eu)                                                                                                                                                                                
Latency                       16ms                                                                                                                                                                                       
Web Interface                 http://127.0.0.1:4040                                                                                                                                                                      
Forwarding                    https://<this>-<is>-<redacted>.ngrok-free.dev -> http://localhost:5001                                                                                                              
                                                                                                                                                                                                                         
Connections                   ttl     opn     rt1     rt5     p50     p90                                                                                                                                                
                              15      0       0.00    0.00    10.77   163.64                                                                                                                                             
HTTP Requests             
```

The important url is `https://<this>-<is>-<redacted>.ngrok-free.dev`, this will be accessible throught the web. The url must be registered in the endpoint section of the App we have created


![alt text](./images/create_app_endpoints.png){ height=100 } 

Additionally to the url, we must give a name and a description to the endpoint and decide to what event the app is subscribing to

![alt text](./images/create_app_endpoints_popup.png){ height=100 } 

Note that we have to append `/webhook` to the url and that for custom chat applications `unique.chat.external-module.chose` is required. 

We can now add the two secrets to `unique.env`

```
UNIQUE_APP_ENDPOINT=https://<this>-<is>-<redacted>.ngrok-free.dev/webhook
UNIQUE_APP_ENDPOINT_SECRET=usig_1pfb5r1LwK9T8yV4gyqBBDwMsvK37KK7kZIxbV1RglA
```

## Setting up a Module and a Space

Wether SSE or Webhooks are use, a AI Module Template and a Space must be setup to send messages to the app.

### Module Templates

Modules Templates establish a base configuration and setup that can be further refined when setting up a space.
Most importantly they define the `reference in Code` that will be passed along with each event and can be used to filter events.

1. Click on  ![alt text](./images/module_button.png){ height=50 } to create a new module using the ![alt text](./images/create_module_button.png){ height=50 } this should open the following page.

![alt text](./images/create_module_full_page.png)

2. Name the Module and give it a unique `Reference in Code`


![alt text](./images/create_module_reference_in_code.png)

3. Define a default configuration that can be refined in the space setup.

4. Define a default definition (this is a function/tool definition ) that must follow the [openai definitions](https://platform.openai.com/docs/guides/function-calling#defining-functions). This is only required for the case where a space hosts multiple modules at the same time.

### Space 

Spaces are shown as assistants and can host multiple modules

1. Click on  ![alt text](./images/space_button.png){ height=50 } and click on the ![alt text](./images/create_space_button.png){ height=50 }. This will lead you to the following page

![alt text](./images/create_space_page.png)

2. Give the space a name

3. Click on custom space and select an AI module template in the following selection

![alt text](./images/create_ai_assistant_space.png)

4. Edit the configuration and definition

![alt text](./images/create_ai_assistant_space_configuration.png)

5. Publish the space in the top right corner and follow the `Go to Chat` link.




## Filtering chat events when using SSE or Webhooks

Chat events are filtered by the following two environment variables

```
UNIQUE_CHAT_EVENT_FILTER_OPTIONS_ASSISTANT_IDS=
UNIQUE_CHAT_EVENT_FILTER_OPTIONS_REFERENCES_IN_CODE=
```

these variables will be automatically caught by the settings and filter the events that reach the handlers.

An example would look as follows

```
UNIQUE_CHAT_EVENT_FILTER_OPTIONS_ASSISTANT_IDS=["assistant_i34ys925m8zi5n6ptobbnwl1"]
UNIQUE_CHAT_EVENT_FILTER_OPTIONS_REFERENCES_IN_CODE=["AcademyTestModule"]
```

⚠️ Events are filtered by default if none of the above variables are defined
️ 




## Service Initialization from Events

Once you have an event, you can initialize services directly from it:

```{.python #init_services_from_event}
# Initialize services from event
chat_service = ChatService(event)
kb_service= KnowledgeBaseService.from_event(event)
```

<!--
```{.python #full_sse_setup}
<<common_imports>>
<<unique_setup_settings_sdk_from_env>>
for event in get_event_generator(unique_settings=settings, event_type=ChatEvent):
```
-->


<!--
```
```{.python #full_sse_setup_with_services file=docs/.python_files/sse_setup_with_services.py}
<<full_sse_setup>>
    <<init_services_from_event>>
```
-->


??? example "Full Examples (Click to expand)"
    
    <!--codeinclude-->
    [Full SSE Setup](../examples_from_docs/sse_setup_with_services.py)
    <!--/codeinclude-->
