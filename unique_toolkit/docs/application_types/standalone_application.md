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

and loaded via the settings class

```{.python #unique_setup_settings_sdk_from_env_standalone}
settings = UniqueSettings.from_env_auto_with_sdk_init()
```

```{.python #unique_init_service_standalone}
content_service = ContentService.from_settings(settings=settings)
```

??? example "Full Examples (Click to expand)"
    
    <!--codeinclude-->
    [Full Standalone](../examples_from_docs/standalone_setup.py)
    <!--/codeinclude-->

<!--
```{.python #standalone_setup file=docs/.python_files/standalone_setup.py}
from unique_toolkit import ContentService
from unique_toolkit.app.unique_settings import UniqueSettings
<<openai_toolkit_imports>>

<<unique_setup_settings_sdk_from_env_standalone>>
<<unique_init_service_standalone>>
client = get_openai_client(unique_settings=settings)
```
-->

