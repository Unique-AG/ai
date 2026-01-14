# Development Setup with Event Socket Streaming Endpoint (SSE)

!!! warning "Development Only - Not for Production"
    **The Event Socket (SSE) is intended for development purposes only.** It has significant limitations including no delivery guarantees, automatic connection timeouts, and no retry mechanisms. **For production use, you must use Webhooks instead.**

Server-Sent Events (SSE) provide a persistent connection to the Unique platform's event stream. This is ideal for local development as it doesn't require exposing a public endpoint or using tunneling services like ngrok.

## Rationale

Unique's ICPs are FSI clients, and specifically their developers (FSI Developer) most often have (for good reasons) heavily governed computers. This interferes with certain software architecture patterns Unique leverages, especially when locally developing with/against them.

Unique AI chat empowers extensibility via its App Repository and the respective Webhook Workers and Schedulers. That means the Unique platform actively _pushes_ content securely to a remote machine that is naturally exposed to the same network.

This _push principle_ is not achievable for some Developers. While there are some workarounds that these Developers could try, most would realistically violate a company policy. Unique does not encourage that, so it introduced the Event Socket, which allows developers to open an event stream from their own machines without the need to open up a public endpoint to the internet.

## Scope

The Event Socket service allows consumers to subscribe to events and open a long-lived HTTP EventSource connection. Events from the Unique AI platform are sent via the connection.

!!! danger "Critical Limitations"
    - **No delivery guarantee**: The connection does not provide any delivery guarantee
    - **Automatic timeout**: Connections automatically close (without warning) after 10 minutes
    - **No retry mechanism**: If the connection is down, events are lost with no replay capability
    - **Development only**: This service must not be used in production environments

For these reasons, the Event Socket should **only** be used for development purposes. For production deployments, use Webhooks instead.

## Architecture

The **Event Socket** is subscribed to the same Event Bus as the Webhook Services. While Webhooks send HTTP requests to registered endpoints with retry mechanisms, the Event Socket publishes events to subscribed consumers via server-sent events.

The Event Socket is a dedicated service that can be scaled independently from the rest of Unique AI to accommodate client needs and scale.

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

By using the **mandatory** `subscriptions` query argument, you can define which events you want to receive via the subscription. **Multiple events can be separated by a comma.**

For example, to subscribe to both user message created and external module chosen events, use the following command:

```bash
...
export SUBSCRIPTIONS=unique.chat.user-message.created,unique.chat.external-module.chosen  
...
```

## Configuration

The following environment variables must be configured in a `unique.env` file or in your environment when developing with SSE:

```env
UNIQUE_API_BASE_URL=            # The backend URL of Unique's public API
UNIQUE_API_VERSION=             # The version of Unique's public API

UNIQUE_APP_ID=                  # The app ID as obtained in the App section of Unique
UNIQUE_APP_KEY=                 # The app key as obtained in the App section of Unique

UNIQUE_AUTH_COMPANY_ID=
UNIQUE_AUTH_USER_ID=
```

For convenience, we provide the `get_event_generator` functionality that hides the complexities of the SSE client. You only need to specify the type of event your application is looking for. Currently, only `ChatEvent` is available, but other events will be added in the future.


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

!!! warning "Important Limitations"
    The Event Socket has critical limitations that make it unsuitable for production use. Please review these carefully before using this service.

### Connection Timeout

!!! danger "10-Minute Timeout"
    **The connection automatically closes after 10 minutes**, regardless of how many events are sent. There is no warning before the connection closes.

    **You must implement proper timeout detection and reconnection logic** to keep receiving events. If your application does not handle reconnection, you will miss events after the timeout period.

### No Delivery Guarantees

!!! danger "No Retry or Replay"
    The Event Socket service has no knowledge of which consumers are supposed to receive events. It only sends events to **active subscriptions**.

    **If your connection is down, events are lost permanently.** There is no:
    - Retry mechanism
    - Replay capability
    - Delivery confirmation
    - Event queuing

    Any events that occur while your connection is not active will not be delivered.

### Production Use

!!! error "Not for Production"
    **For production purposes, you must use Webhooks instead.** Webhooks provide:
    - Reliable delivery with retry mechanisms
    - Persistent event queuing
    - Delivery confirmations
    - Production-grade reliability

## Security Considerations

!!! warning "Security Implications"
    The Event Socket allows developers to connect their local machines directly to test or production systems. This creates security considerations that must be understood and accepted.

### Accessibility

The Event Socket mechanism allows developers to effectively attach their local machines to test or even production systems. This is a scenario that most clients want to actively avoid, which is often the primary reason for not allowing developers to expose their machines in the first place.

### Risk Mitigation

Unique is fully aware of these risks and mitigates them in the following ways:

- **On Behalf Of (OBO) access**: Developers leveraging this mechanism have access to the same data they would already have access to, as the stream operates on behalf of their existing credentials
- **Explicit acknowledgment**: Developers and clients who use this service must actively acknowledge the identified risks in written form and accept the Terms of Use

!!! note "Responsibility"
    By using the Event Socket service, you acknowledge that you understand the security implications and accept responsibility for the risks associated with connecting your local development machine to Unique's systems.

