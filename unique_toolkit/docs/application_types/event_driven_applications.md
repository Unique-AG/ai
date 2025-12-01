# Event Driven App

A event driven application reacts to events obtained from the Unique plattfom. These event can be used to initialize services that in turn have effect on the chat, knowledge base or the agentic table.

For a secure application it is paramount that successive events do not have any effect onto each other, thus ideally your functionality is stateless and all necessary state is obtained via the services of the Unique Plattform.


# Events

The unique platform sends out events to dedictate endpoints (Webhooks) or registered clients (SSE). 

# Development Setup

## Register App in Plattform
Wether we use the SSE client to initiate the connection from the python code or we expose the webhook via an URL, the app need to be registered as explained [here](./event_driven_platform_setup.md)

## Option1: Connecting via SSE Client
Using an SSE client we can connect to the event stream of the unique platform.  Find more [here](./event_driven_with_sse.md).

## Option2: Exposing an Endpoint to the Unique Platform
Setting up an FastAPI application and exposing the local endpoint via ngrok and the web we can register this endpoint directly within the Unique platform
More [here](./event_driven_as_app_with_ngrok.md)


## Filtering Chat Events

Applications using events are responsible to decide how to react to them and to configure what events should be dropped. 
Chat events may be filtered by the following two environment variables

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

⚠️ Events are filtered by default if none of the above variables are defined when using our SSE or FastApi setup.



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



️



