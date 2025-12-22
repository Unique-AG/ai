# Development Setup with Event Socket Streaming Endpoint (SSE)

Server-Sent Events (SSE) provide a persistent connection to the Unique platform's event stream. This is ideal for development as it doesn't require exposing a public endpoint.

## Rationale

Unique's ICPs are FSI clients, and specifically their developers (FSI Developer) most often have (for good reasons) heavily governed computers. This interferes with certain software architecture patterns Unique leverages, especially when locally developing with/against them.

Unique AI chat empowers extensibility via its App Repository and the respective Webhook Workers and Schedulers. That means the Unique platform actively _pushes_ content securely to a remote machine that is naturally exposed to the same network.

This _push principle_ is not achievable for some Developers. While there are some workarounds that these Developers could try, most would realistically violate a company policy. Unique does not encourage that, so it introduced the Event Socket, which allows developers to open an event stream from their own machines without the need to open up a public endpoint to the internet.

## Scope

The Event Socket service allows consumers to subscribe to events and open a long-lived HTTP EventSource connection. Events from the Unique AI platform are sent via the connection.

The connection does not provide any delivery guarantee and automatically closes (without warning) after 10 minutes (also see Limitations below).

For these reasons, Unique discourages any use of the Event Socket in any non-development use cases.

## Architecture

The **Event Socket** is subscribed to the same Event Bus as the Webhook Services themselves. While the Webhooks send HTTP requests to registered endpoints with retry mechanisms, the Event Socket will publish events to subscribed consumers via server-sent events.

The Event Socket is a dedicated service that can be scaled independently from the rest of Unique AI to accommodate the client's needs and scale.

### Event Socket Endpoint

In order to receive events from the Event Socket service, consumers must open an EventSource stream to the Event Socket service:

```bash
export BASE_URL=gateway.<tenant>.unique.app
export SUBSCRIPTIONS=unique.chat.user-message.created
curl --location "https://$BASE_URL/public/event-socket/events/stream?subscriptions=$SUBSCRIPTIONS" \
  --header 'x-app-id: <UNIQUE-APP-ID>' \
  --header 'x-company-id: <UNIQUE-COMPANY-ID>' \
  --header 'Authorization: Bearer <API-KEY>'
```

The endpoint is secured like all other Public API endpoints and requires:
- `x-app-id`: Your Unique App ID
- `x-company-id`: The current company ID
- `Authorization`: Bearer token with your API key

By using the **mandatory** `subscriptions` query argument, the consumer can define which events they want to receive via the subscription. **Multiple events can be separated by a comma.**
For instance to subscribe to both user message created and external module chosen events, the following command can be used:

```bash
...
export SUBSCRIPTIONS=unique.chat.user-message.created,unique.chat.external-module.chosen  
...
```

## Configuration

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
    [Full SSE Setup](./../../examples_from_docs/sse_setup_with_services.py)
    <!--/codeinclude-->


## Limitations

### Timeout

The connection will timeout after 10 minutes, no matter how many events are sent over the line. The consumer must implement a proper timeout detection and re-new the subscription to keep receiving events.

### No Retry

The Event Socket service has no knowledge of which consumers are supposed to receive events. It only sends events to active subscriptions. If the connection is not up and running, the consumer application will not receive any events and there is no replay or retry mechanism.

For production purposes, Webhooks must be used.

## Security

### Accessibility

These mechanisms allow developers to de-facto attach their machines to a test or even production system, a scenario most clients want to actively avoid (mainly a reason in the first place not even to allow developers to expose their machines).

Unique is fully aware of this risk and mitigates it in the following ways:

* Developers leveraging this mechanism have access to the same data already, as the stream is On Behalf Of (_OBO_).
* Developers and clients who want to leverage these services have actively acknowledged the identified risks in a written form and are accepting the Terms of Use.

