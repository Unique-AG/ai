from pydantic_settings import SettingsConfigDict

CHAT_EVENT_FILTER_OPTIONS_SETTINGS = SettingsConfigDict(
    env_prefix="unique_chat_event_filter_options_",
    env_file_encoding="utf-8",
    case_sensitive=False,
    extra="ignore",
)
