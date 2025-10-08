# Standalone App

A standalone application uses the capabilities of the Unique plattform but is not interacting with the users directly via any GUI.

## Examples

- Knowledgebase Management Pipeline
- Automatic Report Generation

# Initializing the SDK and Toolkit Services

For standalone service the following secrets must available in the environment be placed within the `unique.env` file. [More info](../setup/getting_started.md).

```env
UNIQUE_API_BASE_URL=            # The backend url of Unique's public API
UNIQUE_API_VERSION=             # The version Unique's public API

UNIQUE_APP_ID=                  # The app id as obtained in the App secion of Unique
UNIQUE_APP_KEY=                 # The app key as obtained in the App secion of Unique

UNIQUE_AUTH_COMPANY_ID=
UNIQUE_AUTH_USER_ID=
```

These environment variables are loaded implicitely throught `UniqueSettings` that can be passed to the services as

<!--
```{.python #unique_setup_settings_sdk_from_env_standalone}
settings = UniqueSettings.from_env_auto_with_sdk_init()
```
-->

```{.python #unique_init_service_standalone}
kb_service = KnowledgeBaseService.from_settings(settings=settings)
```

if it is not passed it is automatically loaded such that the services can be initialized as

```{.python #unique_init_service_standalone_auto}
kb_service = KnowledgeBaseService.from_settings()
```

??? example "Full Examples (Click to expand)"
    
    <!--codeinclude-->
    [Standalone Init](../examples_from_docs/standalone_setup.py)
    [Auto Standalone Init](../examples_from_docs/standalone_setup_auto.py)
    <!--/codeinclude-->

<!--
```{.python file=docs/.python_files/standalone_setup.py}
<<common_imports>>
<<unique_setup_settings_sdk_from_env_standalone>>
<<unique_init_service_standalone>>
client = get_openai_client(unique_settings=settings)
```
-->


<!--
```{.python file=docs/.python_files/standalone_setup_auto.py}
<<common_imports>>
<<unique_init_service_standalone_auto>>
client = get_openai_client()
```
-->

