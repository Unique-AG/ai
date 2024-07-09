import os

import unique_sdk


def init_sdk():
    """Initializes the SDK."""
    unique_sdk.api_base = os.environ.get("API_BASE")  # Required

    # Optional if being run locally
    unique_sdk.api_key = os.environ.get(
        "API_KEY", "dummy"
    )  # Optional if being run locally
    unique_sdk.app_id = os.environ.get(
        "APP_ID", "dummy"
    )  # Optional if being run locally
    endpoint_secret = os.environ.get("ENDPOINT_SECRET", None)

    return endpoint_secret
