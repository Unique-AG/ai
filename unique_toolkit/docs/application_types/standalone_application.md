# Standalone Applications

A standalone application uses the capabilities of the Unique plattform but is not interacting with the users directly.

## Examples

- Knowledgebase Management Pipeline
- Automatic Report Generation

## Secrets

The following secrets need to be setup in a `.env` file or in the environment

```env
UNIQUE_AUTH_ORDER_ID=           # Your company id
UNIQUE_AUTH_USER_ID=            # Your user id

UNIQUE_API_BASE_URL=            # The backend url of Unique's public API
UNIQUE_API_VERSION=             # The version Unique's public API

UNIQUE_APP_ID=                  # The app id as obtained in the App secion of Unique
UNIQUE_APP_KEY=                 # The app key as obtained in the App secion of Unique
```


# Initializing the SDK and Toolkit Services

Standalone applications services need to know the `user_id` and `company_id` 

``` {.python }
content_service = ContentService.from_settings(
    company_id=...
    user_id=...
)
```

and the sdk can be configured by

```{.python}
unique_sdk.app_id = ...   (UNIQUE_APP_ID)
unique_sdk.api_key = ...  (UNIQUE_APP_KEY)
unique_sdk.api_base = ... (UNIQUE_API_BASE_URL)
```

If the UniqueSettings object is initiallized, the  `init_unique_sdk` utility and the `from_settings` method of the services help with this

``` {.python #initialize_content_service_standalone}
from pathlib import Path
from unique_toolkit.app.init_sdk import init_unique_sdk
from unique_toolkit import ContentService, LanguageModelService, EmbeddingService
from unique_toolkit.app.unique_settings import UniqueSettings

settings = UniqueSettings.from_env(env_file=Path("../.env"))

init_unique_sdk(unique_settings=settings)

content_service = ContentService.from_settings(settings=settings)
llm_service = LanguageModelService.from_settings(settings=settings)
embedding_service = EmbeddingService.from_settings(settings=settings)

# Your application logic here
```



Now you can initialise the services 