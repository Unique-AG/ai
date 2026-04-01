from pydantic_settings import SettingsConfigDict

from unique_toolkit.app.find_env_file import find_env_file

CHAT_EVENT_FILTER_OPTIONS_SETTINGS = SettingsConfigDict(
    env_prefix="unique_chat_event_filter_options_",
    env_file_encoding="utf-8",
    case_sensitive=False,
    extra="ignore",
    env_file=find_env_file("unique.env", ".env", required=False),
)
