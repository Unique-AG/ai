import os
import unique_sdk

def get_env(var_name, default=None, strict=False):
    """Get the environment variable.

    Args:
        var_name (str): Name of the environment variable.
        default (str, optional): Default value. Defaults to None.
        strict (bool, optional): This method raises a ValueError, if strict, and no value is found in the environment. Defaults to False.

    Raises:
        ValueError: _description_

    Returns:
        _type_: _description_
    """
    val = os.environ.get(var_name)
    if not val:
        if strict:
            raise ValueError(f"{var_name} is not set")
    return val or default


def init_sdk(strict_all_vars=False):
    """Initialize the SDK.

    Args:
        strict_all_vars (bool, optional): This method raises a ValueError if strict and no value is found in the environment. Defaults to False.
    """
    unique_sdk.api_key = get_env("API_KEY", default="dummy", strict=strict_all_vars)
    unique_sdk.app_id = get_env("APP_ID", default="dummy", strict=strict_all_vars)
    unique_sdk.api_base = get_env("API_BASE", default=None, strict=strict_all_vars)


def get_endpoint_secret():
    """Fetch endpoint secret from the environment."""
    endpoint_secret = os.getenv("ENDPOINT_SECRET")
    return endpoint_secret
