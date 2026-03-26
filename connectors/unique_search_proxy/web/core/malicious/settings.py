from unique_toolkit.app.init_sdk import UniqueSettings


def init_malicious_sdk() -> UniqueSettings:
    """Initialize the unique SDK and return settings with auth context.

    Reads auth from env vars (COMPANY_ID, USER_ID, APP_KEY, APP_ID, etc.)
    already loaded by load_dotenv() in app.py, or from a unique.env file.
    """
    settings = UniqueSettings.from_env()
    settings.init_sdk()
    return settings
