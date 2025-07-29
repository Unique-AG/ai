# Standalone application

A standalone application uses the capabilities of the Unique plattform but is not interacting with the users directly.

## Examples

- Knowledgebase Management Pipeline
- Automatic Report Generation

## Secrets

The following secrets need to be setup in a `.env` file or in the environment

```env
UNIQUE_AUTH_ORDER_ID= # Your company id
UNIQUE_AUTH_USER_ID=  # Your user id
UNIQUE_API_BASE_URL=  # The backend url of Unique's public API
UNIQUE_API_VERSION=   # The version Unique's public API
```

## Init the SDK

Before you can use the unique toolkit the unique sdk has to be initialized, this can be done using the
convenience method. 

```{.python #init_sdk_imports_from_environment}
from unique_toolkit.app import init_unique_sdk
init_unique_sdk()
```
or 
```{.python #init_sdk_imports_from_file}
from unique_toolkit.app import init_unique_sdk
init_unique_sdk(env_file=<path to your .env file>)
```

The former initialization directly from the the environent, while the later uses a `.env` file.
