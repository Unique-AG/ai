# %%
# Check API connection
# Run each cell with the debugger to inspect the result interactively.

import asyncio

from unique_toolkit.app.unique_settings import (
    UniqueApi,
    UniqueApiConnectionError,
    UniqueSettings,
)

# %%

# Load settings from environment (reads UNIQUE_* env vars or a .env file).
settings = UniqueSettings.from_env_auto_with_sdk_init()

# %%

# Show the resolved SDK URL that the SDK will use.
print("SDK URL:", settings.api.sdk_url())

# %%

# Check the connection — returns True if at least one model is available,
# False if connected but no models are configured,
# raises UniqueApiConnectionError on network/auth failures.
try:
    connected = asyncio.run(settings.check_connection())
    print("Connected:", connected)
except UniqueApiConnectionError as exc:
    print("Connection failed:", exc)
    print("Base URL used:", exc.base_url)

# %%

# You can also point at a different environment by swapping the api field.
qa_settings = UniqueSettings(
    auth=settings.auth,
    app=settings.app,
    api=UniqueApi(base_url="https://gateway.qa.unique.app/unique-api/"),
)

try:
    connected = asyncio.run(qa_settings.check_connection())
    print("QA connected:", connected)
except UniqueApiConnectionError as exc:
    print("QA connection failed:", exc)

# %%
