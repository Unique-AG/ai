import os

import unique_sdk


def init_sdk():
    """Initializes the SDK."""
    unique_sdk.api_key = get_env("API_KEY")
    unique_sdk.app_id = get_env("APP_ID")
    api_base = os.environ.get("API_BASE")
    if api_base:
        unique_sdk.api_base = api_base

    endpoint_secret = get_env("ENDPOINT_SECRET")
    return endpoint_secret

def get_env(var_name):
    val = os.environ.get(var_name)
    if not val:
        raise ValueError(f"{var_name} is not set")
    return val