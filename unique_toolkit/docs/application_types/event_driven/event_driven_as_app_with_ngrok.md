# Development Setup with Webhooks and ngrok

This setup allows you to expose a local webhook application (FastAPI, Quart, Flask, etc.) to the Unique platform using ngrok as a tunnel. This is useful for local development when you want to test webhook endpoints.

## Configuration

The following secrets must be configured for this in an `unique.env` file or in the environment when developing with webhooks

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
    [Custom Application with FastAPI](./../../examples_from_docs/fastapi_app_minimal.py)
    <!--/codeinclude-->


This can be run using the debugger and will be exposed locally under `http://localhost:5001`. To make the application available to the platform we can expose it using [ngrok](https://ngrok.com/), therefore we execute 

```
ngrok http 5001
```

on the command line. This will open a live console with the following content 

```
ngrok

⚠️ Free Users: Agents ≤3.18.x stop connecting 12/17/25. Update or upgrade: https://ngrok.com/

pricing

Session Status
online
Account                       <redacted> (Plan:Free)
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


![alt text](./../images/create_app_endpoints.png){ height=100 } 

Additionally to the url, we must give a name and a description to the endpoint and decide to what event the app is subscribing to

![alt text](./../images/create_app_endpoints_popup.png){ height=100 } 

Note that we have to append `/webhook` to the url and that for custom chat applications `unique.chat.external-module.chose` is required. 

We can now add the two secrets to `unique.env`

```
UNIQUE_APP_ENDPOINT=https://<this>-<is>-<redacted>.ngrok-free.dev/webhook
UNIQUE_APP_ENDPOINT_SECRET=usig_<redacted>
```



## Troubleshooting

### ngrok Issues

- **URL changes on restart**: This is expected with the free tier. Update `UNIQUE_APP_ENDPOINT` in your environment and re-register the endpoint in the platform
- **Connection refused**: Ensure your FastAPI app is running on the correct port (default: 5001)
- **ngrok not starting**: Check if port 4040 is already in use (ngrok web interface)

### Webhook Not Receiving Events

- **Endpoint not registered**: Verify the endpoint is registered in the platform with the correct URL (including `/webhook`)
- **Wrong event subscription**: Ensure you've subscribed to `unique.chat.external-module.chose` for chat events
- **URL mismatch**: The URL in your environment must exactly match the one registered in the platform
- **Secret mismatch**: Verify `UNIQUE_APP_ENDPOINT_SECRET` matches the secret from the platform



### Debugging Tips

- Check ngrok web interface at `http://127.0.0.1:4040` to see incoming requests
- Enable debug logging in your FastAPI app
- Verify the webhook is being called by checking ngrok request logs
- Test the endpoint locally first before exposing via ngrok

 



