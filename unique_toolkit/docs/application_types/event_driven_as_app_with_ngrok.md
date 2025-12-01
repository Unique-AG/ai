# Development Setup with Webhooks and ngrok

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


![alt text](./images/create_app_endpoints.png){ height=100 } 

Additionally to the url, we must give a name and a description to the endpoint and decide to what event the app is subscribing to

![alt text](./images/create_app_endpoints_popup.png){ height=100 } 

Note that we have to append `/webhook` to the url and that for custom chat applications `unique.chat.external-module.chose` is required. 

We can now add the two secrets to `unique.env`

```
UNIQUE_APP_ENDPOINT=https://<this>-<is>-<redacted>.ngrok-free.dev/webhook
UNIQUE_APP_ENDPOINT_SECRET=usig_<redacted>
```




 



