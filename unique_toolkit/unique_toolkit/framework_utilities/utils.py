from unique_toolkit.app.unique_settings import UniqueApp, UniqueAuth


def auth_headers(auth_settings: UniqueAuth) -> dict[str, str]:
    return {
        "x-user-id": auth_settings.user_id.get_secret_value(),
        "x-company-id": auth_settings.company_id.get_secret_value(),
    }


def app_headers(app_settings: UniqueApp) -> dict[str, str]:
    return {
        "x-app-id": app_settings.id.get_secret_value(),
        "Authorization": f"Bearer {app_settings.key.get_secret_value()}",
    }


def get_default_headers(app_settings: UniqueApp, auth_settings: UniqueAuth):
    default_headers = {}
    default_headers.update(app_headers(app_settings))
    default_headers.update(auth_headers(auth_settings))
    default_headers["x-api-version"] = "2023-12-06"
    return default_headers
