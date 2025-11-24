# Environment Setup

## Installation

Unique Toolkit is available on [PyPI](https://pypi.org/project/unique_toolkit/) and can be installed using `pip`/`poetry` or `uv`:

We highly recommend using a virtual environment to install Unique Toolkit.


## Minimal Project Setup

Here we use [`uv`](https://docs.astral.sh/uv/) to setup a minimal project. In the terminal use

```
uv init my_unique_project
```

to create a project which results in 

```
❯ tree my_unique_project 
my_unique_project
├── main.py
├── pyproject.toml
└── README.md
```

then we change into the folder and add the `unique_toolkit` as a dependency

```
cd my_unique_project 
uv add unique_toolkit
```

## Setting up Examples

If you want to explore the examples within a project you can download them using the following code

```
REPO=https://github.com/Unique-AG/ai.git
mkdir examples
git clone --depth 1 --filter=blob:none --sparse $REPO temp-repo

cd temp-repo
git sparse-checkout set unique_toolkit/docs/examples_from_docs
cp -r unique_toolkit/docs/examples_from_docs/ ../examples

cd ..
rm -rf temp-repo
```

this will download all the examples from the documentation into a folder called `examples`.


**Setting up Secrets for Examples**

The following secrets must be set up in a file with the name `unique.env` at the root of the project.

```env
UNIQUE_AUTH_COMPANY_ID=                         # Your company id
UNIQUE_AUTH_USER_ID=                            # Your user id

UNIQUE_API_BASE_URL=                            # The backend url of Unique's public API
UNIQUE_API_VERSION=                             # The version Unique's public API

UNIQUE_APP_ID=                                  # The app id as obtained in the App section of Unique
UNIQUE_APP_KEY=                                 # The app key as obtained in the App section of Unique
```

<!--

## Secrets and how to find them

The following secrets need to be setup in a `unique.env` file located as described below or in the environment

```env
UNIQUE_AUTH_COMPANY_ID=                         # Your company id
UNIQUE_AUTH_USER_ID=                            # Your user id

UNIQUE_API_BASE_URL=                            # The backend url of Unique's public API
UNIQUE_API_VERSION=                             # The version Unique's public API

UNIQUE_APP_ID=                                  # The app id as obtained in the App section of Unique
UNIQUE_APP_KEY=                                 # The app key as obtained in the App section of Unique

# Optional: Event filtering options (JSON format)
# Filter events by specific assistant IDs (JSON array format)
UNIQUE_CHAT_EVENT_FILTER_OPTIONS_ASSISTANT_IDS=["assistant1", "assistant2"]

# Filter events by specific module/reference names (JSON array format)  
UNIQUE_CHAT_EVENT_FILTER_OPTIONS_REFERENCES_IN_CODE=["module1", "module2"]
```
-->

??? info "Environment File Locations (Click to expand)"
    
    The toolkit automatically searches for your `unique.env` file in the following locations (in order of priority):

    ### 1. Custom Location (Highest Priority)
    Set the `UNIQUE_ENV_FILE` environment variable to specify a custom location:

    ```bash
    # Linux/macOS
    export UNIQUE_ENV_FILE="/path/to/your/custom/unique.env"

    # Windows PowerShell
    $env:UNIQUE_ENV_FILE = "C:\path\to\your\custom\unique.env"

    # Windows Command Prompt
    set UNIQUE_ENV_FILE=C:\path\to\your\custom\unique.env
    ```

    ### 2. Current Working Directory
    ```
    ./unique.env
    ```
    The toolkit will look for `unique.env` in the directory where you run your script.

    ### 3. User Configuration Directory (Recommended)

    The toolkit follows operating system conventions for configuration files:

    #### Linux/Unix
    ```
    ~/.config/unique/unique.env
    ```

    #### macOS
    ```
    ~/Library/Application Support/unique/unique.env
    ```

    !!! tip "Alternative for macOS"
        You can also use the Linux-style path on macOS: `~/.config/unique/unique.env`

    #### Windows
    ```
    %APPDATA%\unique\unique.env
    ```


These secrets can be obtained by inspecting you **Personal API Key** section that can be found when clicking onto your account in the top right corner of the frontend

![alt text](./images/personal_api_key_location.png){ width=300 }

On clicking onto the personal api key button the following popup appears 

![alt text](./images/personal_api_key.png)

and the secrets must be used according to the following table into the environment variables

| Toolkit Secret Variable | Platform Secret Name | Example | 
|--|--|--|
|UNIQUE_AUTH_COMPANY_ID | Company ID| `346386357988860534` |
|UNIQUE_AUTH_USER_ID | User ID | `347188092944093062` |
|UNIQUE_APP_ID | App ID | `app_iaii8qhvt5j80wo9i4wmwqqc` |
|UNIQUE_APP_KEY | Api Key | `ukey_yoegC20rdtKPT50cOX8MnrAaGetPX5Bg8Zc1tC7Nkbc`|

The `UNIQUE_API_BASE_URL` can be obtained from your admin and the current `UNIQUE_API_VERSION` is `2023-12-06`.


<!--
### Filtering Events
Filtering on events is possible via additional environment variables 

| Variable | Event Type | Value Type | Help |
|--|--|--|--|
|`UNIQUE_CHAT_EVENT_FILTER_OPTIONS_REFERENCES_IN_CODE` | `ChatEvent` | `list[str]` | The reference in code of a module found in the `AI Modules Templates` section for each module and can be found just below the module title| 
|`UNIQUE_CHAT_EVENT_FILTER_OPTIONS_ASSISTANT_IDS` | `ChatEvent` | `list[str]` | The assistant id of a space can be taken from the URL when you configure a Space. It starts with `assistant_..`|


## App endpoint

An app endpoint is required in the production scenario when the app is running in a container. In this case the Unique plattform reaches the app via the registered endpoints.

[WIP]
-->