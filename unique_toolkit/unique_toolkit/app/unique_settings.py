from __future__ import annotations

from logging import getLogger
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self, TypeVar
from urllib.parse import ParseResult, urlparse, urlunparse

import unique_sdk
from pydantic import (
    AliasChoices,
    BaseModel,
    Field,
    PrivateAttr,
    SecretStr,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Protocol, deprecated

from unique_toolkit._common.config_checker import register_config
from unique_toolkit.app.chat_event_filter_options_settings import (
    CHAT_EVENT_FILTER_OPTIONS_SETTINGS,
)
from unique_toolkit.app.feature_flags import UNIQUE_TOOLKIT_FEATURE_FLAGS
from unique_toolkit.app.find_env_file import EnvFileNotFoundError, find_env_file

if TYPE_CHECKING:
    from unique_toolkit.app.schemas import BaseEvent, ChatEvent


logger = getLogger(__name__)

T = TypeVar("T", bound=BaseSettings)


def warn_about_defaults(instance: T) -> T:
    """Log warnings for fields that are using default values."""
    for field_name, model_field in instance.__class__.model_fields.items():
        field_value = getattr(instance, field_name)
        default_value = model_field.default

        # Handle SecretStr comparison by comparing the secret values
        if isinstance(field_value, SecretStr) and isinstance(default_value, SecretStr):
            if field_value.get_secret_value() == default_value.get_secret_value():
                logger.warning(
                    f"Using default value for '{field_name}': {default_value.get_secret_value()}"
                )
        elif field_value == default_value:
            logger.warning(f"Using default value for '{field_name}': {default_value}")
    return instance


# Auth
# We have a BaseModel and a BaseSetting class here because the context can be
# obtained from the environment and or a request. In the case of a request we
# should be using the AuthContext.
# Both classes implement the protocol that can be used for typing.
class AuthContextProtocol(Protocol):
    company_id: SecretStr
    user_id: SecretStr

    def get_confidential_company_id(self) -> str: ...
    def get_confidential_user_id(self) -> str: ...


class AuthContext(BaseModel):
    company_id: SecretStr = Field(
        ...,
        description="The company ID.",
        frozen=UNIQUE_TOOLKIT_FEATURE_FLAGS.un_18894_freeze_unique_settings.is_enabled(),
    )
    user_id: SecretStr = Field(
        ...,
        description="The user ID.",
        frozen=UNIQUE_TOOLKIT_FEATURE_FLAGS.un_18894_freeze_unique_settings.is_enabled(),
    )

    def get_confidential_company_id(self) -> str:
        return self.company_id.get_secret_value()

    def get_confidential_user_id(self) -> str:
        return self.user_id.get_secret_value()

    @classmethod
    def from_event(cls, event: BaseEvent[Any]) -> Self:
        return cls(
            company_id=SecretStr(event.company_id),
            user_id=SecretStr(event.user_id),
        )


@register_config()
class UniqueAuth(BaseSettings):
    company_id: SecretStr = Field(
        default=SecretStr("dummy_company_id"),
        validation_alias=AliasChoices(
            "unique_auth_company_id",
            "company_id",
            "UNIQUE_AUTH_COMPANY_ID",
            "COMPANY_ID",
        ),
        frozen=UNIQUE_TOOLKIT_FEATURE_FLAGS.un_18894_freeze_unique_settings.is_enabled(),
    )
    user_id: SecretStr = Field(
        default=SecretStr("dummy_user_id"),
        validation_alias=AliasChoices(
            "unique_auth_user_id", "user_id", "UNIQUE_AUTH_USER_ID", "USER_ID"
        ),
        frozen=UNIQUE_TOOLKIT_FEATURE_FLAGS.un_18894_freeze_unique_settings.is_enabled(),
    )

    model_config = SettingsConfigDict(
        env_prefix="unique_auth_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        frozen=UNIQUE_TOOLKIT_FEATURE_FLAGS.un_18894_freeze_unique_settings.is_enabled(),
        env_file=find_env_file("unique.env", ".env", required=False),
    )

    def get_confidential_company_id(self) -> str:
        return self.company_id.get_secret_value()

    def get_confidential_user_id(self) -> str:
        return self.user_id.get_secret_value()

    @model_validator(mode="after")
    def _warn_about_defaults(self) -> Self:
        return warn_about_defaults(self)

    @classmethod
    def from_event(cls, event: BaseEvent[Any]) -> Self:
        return cls(
            company_id=SecretStr(event.company_id),
            user_id=SecretStr(event.user_id),
        )

    def to_auth_context(self) -> AuthContext:
        return AuthContext(
            company_id=self.company_id,
            user_id=self.user_id,
        )


# Chat
class ChatContextProtocol(Protocol):
    chat_id: str
    assistant_id: str

    @property
    def last_assistant_message_id(self) -> str: ...
    @property
    def last_user_message_id(self) -> str: ...
    @property
    def last_user_message_text(self) -> str: ...

    @property
    def metadata_filter(self) -> dict[str, Any] | None: ...
    @property
    def parent_chat_id(self) -> str | None: ...


class ChatContext(BaseModel):
    chat_id: str = Field(
        ...,
        description="The chat ID.",
        frozen=UNIQUE_TOOLKIT_FEATURE_FLAGS.un_18894_freeze_unique_settings.is_enabled(),
    )
    assistant_id: str = Field(
        ...,
        description="The assistant ID.",
        frozen=UNIQUE_TOOLKIT_FEATURE_FLAGS.un_18894_freeze_unique_settings.is_enabled(),
    )

    _last_assistant_message_id: str | None = PrivateAttr(default=None)
    _last_user_message_id: str | None = PrivateAttr(default=None)
    _last_user_message_text: str | None = PrivateAttr(default=None)
    _metadata_filter: dict[str, Any] | None = PrivateAttr(default=None)
    _parent_chat_id: str | None = PrivateAttr(default=None)

    def __init__(
        self,
        *,
        chat_id: str,
        assistant_id: str,
        last_assistant_message_id: str | None = None,
        last_user_message_id: str | None = None,
        last_user_message_text: str | None = None,
        metadata_filter: dict[str, Any] | None = None,
        parent_chat_id: str | None = None,
        **data: Any,
    ) -> None:
        super().__init__(chat_id=chat_id, assistant_id=assistant_id, **data)
        if last_assistant_message_id is not None:
            self._last_assistant_message_id = last_assistant_message_id
        if last_user_message_id is not None:
            self._last_user_message_id = last_user_message_id
        if last_user_message_text is not None:
            self._last_user_message_text = last_user_message_text
        if metadata_filter is not None:
            self._metadata_filter = metadata_filter
        if parent_chat_id is not None:
            self._parent_chat_id = parent_chat_id

    @property
    def last_assistant_message_id(self) -> str:
        if self._last_assistant_message_id is None:
            raise ValueError("Last assistant message id is not set")
        return self._last_assistant_message_id

    @property
    def last_user_message_id(self) -> str:
        if self._last_user_message_id is None:
            raise ValueError("User message id is not set")
        return self._last_user_message_id

    @property
    def last_user_message_text(self) -> str:
        if self._last_user_message_text is None:
            raise ValueError("User message text is not set")
        return self._last_user_message_text

    @property
    def metadata_filter(self) -> dict[str, Any] | None:
        return self._metadata_filter

    @metadata_filter.setter
    def metadata_filter(self, value: dict[str, Any]) -> None:
        self._metadata_filter = value

    @property
    def parent_chat_id(self) -> str | None:
        return self._parent_chat_id

    @parent_chat_id.setter
    def parent_chat_id(self, value: str) -> None:
        self._parent_chat_id = value

    @classmethod
    def from_chat_event(cls, event: ChatEvent) -> Self:
        return cls(
            chat_id=event.payload.chat_id,
            assistant_id=event.payload.assistant_id,
            last_assistant_message_id=event.payload.assistant_message.id,
            last_user_message_id=event.payload.user_message.id
            if event.payload.user_message
            else None,
            last_user_message_text=event.payload.user_message.text
            if event.payload.user_message
            else None,
            metadata_filter=event.payload.metadata_filter
            if event.payload.metadata_filter
            else None,
            parent_chat_id=event.payload.correlation.parent_chat_id
            if event.payload.correlation
            else None,
        )


# App
# Settings only as only obtained from the environment.
@register_config()
class UniqueApp(BaseSettings):
    id: SecretStr = Field(
        default=SecretStr("dummy_id"),
        validation_alias=AliasChoices(
            "unique_app_id", "app_id", "UNIQUE_APP_ID", "APP_ID"
        ),
    )
    key: SecretStr = Field(
        default=SecretStr("dummy_key"),
        validation_alias=AliasChoices(
            "unique_app_key", "key", "UNIQUE_APP_KEY", "KEY", "API_KEY", "api_key"
        ),
    )
    base_url: str = Field(
        default="http://localhost:8092/",
        deprecated="Use UniqueApi.base_url instead",
    )

    endpoint: str = Field(default="dummy")

    endpoint_secret: SecretStr = Field(
        default=SecretStr("dummy_secret"),
        validation_alias=AliasChoices(
            "unique_app_endpoint_secret",
            "endpoint_secret",
            "UNIQUE_APP_ENDPOINT_SECRET",
            "ENDPOINT_SECRET",
        ),
    )

    @model_validator(mode="after")
    def _warn_about_defaults(self) -> Self:
        return warn_about_defaults(self)

    model_config = SettingsConfigDict(
        env_prefix="unique_app_",
        env_file_encoding="utf-8",
        env_file=find_env_file("unique.env", ".env", required=False),
        case_sensitive=False,
        extra="ignore",
        validate_by_name=True,
        validate_by_alias=True,
        frozen=UNIQUE_TOOLKIT_FEATURE_FLAGS.un_18894_freeze_unique_settings.is_enabled(),
    )


# Api
# Settings only as only obtained from the environment.


@register_config()
class UniqueApi(BaseSettings):
    base_url: str = Field(
        default="http://localhost:8092/",
        description="The base URL of the Unique API. Ask your admin to provide you with the correct URL.",
        validation_alias=AliasChoices(
            "unique_api_base_url",
            "base_url",
            "UNIQUE_API_BASE_URL",
            "BASE_URL",
            "API_BASE",
        ),
    )
    version: str = Field(
        default="2023-12-06",
        validation_alias=AliasChoices(
            "unique_api_version", "version", "UNIQUE_API_VERSION", "VERSION"
        ),
    )

    model_config = SettingsConfigDict(
        env_prefix="unique_api_",
        env_file_encoding="utf-8",
        env_file=find_env_file("unique.env", ".env", required=False),
        case_sensitive=False,
        extra="ignore",
        frozen=UNIQUE_TOOLKIT_FEATURE_FLAGS.un_18894_freeze_unique_settings.is_enabled(),
    )

    @model_validator(mode="after")
    def _warn_about_defaults(self) -> Self:
        return warn_about_defaults(self)

    def sse_url(self, subscriptions: list[str]) -> str:
        parsed = urlparse(self.base_url)
        return urlunparse(
            parsed._replace(
                path="/public/event-socket/events/stream",
                query=f"subscriptions={','.join(subscriptions)}",
                fragment=None,
            )
        )

    def base_path(self) -> tuple[ParseResult, str]:
        parsed = urlparse(self.base_url)
        base_path = "/public/chat"

        if parsed.hostname and (
            "gateway.qa.unique" in parsed.hostname
            or "gateway.unique" in parsed.hostname
        ):
            base_path = "/public/chat-gen2"

        if parsed.hostname and (
            "localhost" in parsed.hostname
            or "svc.cluster.local" in parsed.hostname
            or ".svc." in parsed.hostname
            or parsed.hostname.endswith(".svc")
        ):
            base_path = "/public"

        return parsed, base_path

    def sdk_url(self) -> str:
        parsed, base_path = self.base_path()
        return urlunparse(parsed._replace(path=base_path, query=None, fragment=None))

    def openai_proxy_url(self) -> str:
        parsed, base_path = self.base_path()
        path = base_path + "/openai-proxy"
        return urlunparse(parsed._replace(path=path, query=None, fragment=None))


# EventFilterOptions
# Settings only as only obtained from the environment.
class UniqueChatEventFilterOptions(BaseSettings):
    # Empty string evals to False
    assistant_ids: list[str] = Field(
        default=[],
        description="The assistant ids (space) to filter by. Default is all assistants.",
    )
    references_in_code: list[str] = Field(
        default=[],
        description="The module (reference) names in code to filter by. Default is all modules.",
    )

    model_config = CHAT_EVENT_FILTER_OPTIONS_SETTINGS

    @model_validator(mode="after")
    def _warn_about_defaults(self) -> Self:
        return warn_about_defaults(self)


class UniqueEnvironment:
    """
    Contains all settings that come exclusively from the environment.
    This means if a setting can be initialized from either request or the environment, this class will not contain it.
    """

    def __init__(self, app: UniqueApp, api: UniqueApi) -> None:
        self._app = app
        self._api = api

    @property
    def app(self) -> UniqueApp:
        return self._app

    @property
    def api(self) -> UniqueApi:
        return self._api


class UniqueContext:
    """
    Contains all settings/configuration that come from a request or an environment.
    """

    def __init__(
        self,
        auth: AuthContextProtocol | None = None,
        chat: ChatContextProtocol | None = None,
    ) -> None:
        self._auth = auth
        self._chat = chat

    @property
    def auth(self) -> AuthContextProtocol:
        if self._auth is None:
            raise ValueError("Auth context not set")
        return self._auth

    @auth.setter
    @deprecated(
        "Avoid this, rather create a new request context with the new auth context. Kept for backwards compatibility."
    )
    def auth(self, value: AuthContextProtocol) -> None:
        self._auth = value

    @property
    def chat(self) -> ChatContextProtocol | None:
        return self._chat

    @classmethod
    def from_chat_event(cls, event: ChatEvent) -> UniqueContext:
        """Build a full (auth + chat) context from a ChatEvent."""

        return cls(
            auth=AuthContext.from_event(event),
            chat=ChatContext.from_chat_event(event),
        )

    @classmethod
    def from_event(cls, event: BaseEvent[Any]) -> Self:
        """Build an auth-only context from any BaseEvent."""
        return cls(
            auth=AuthContext.from_event(event),
        )

    @classmethod
    def from_settings(cls, settings: UniqueSettings | None = None) -> UniqueContext:
        """Build an auth-only context from UniqueSettings (auto-loads from env if None)."""
        if settings is None:
            settings = UniqueSettings.from_env_auto_with_sdk_init()
        return cls(auth=settings.authcontext)


# Bundling: Build this object for every request.
class UniqueSettings:
    def __init__(
        self,
        auth: AuthContextProtocol,
        app: UniqueApp,
        api: UniqueApi,
        *,
        chat_event_filter_options: UniqueChatEventFilterOptions | None = None,
        chat: ChatContextProtocol | None = None,
        env_file: Path | None = None,
    ):
        self._env = UniqueEnvironment(app=app, api=api)
        self._context = UniqueContext(auth=auth, chat=chat)
        self._chat_event_filter_options = chat_event_filter_options
        self._env_file: Path | None = (
            env_file if (env_file and env_file.exists()) else None
        )

    @classmethod
    def from_env(
        cls,
        env_file: Path | None = None,
    ) -> UniqueSettings:
        """Initialize settings from environment variables and/or env file.

        Args:
            env_file: Optional path to environment file. If provided, will load variables from this file.

        Returns:
            UniqueSettings instance with values loaded from environment/env file.

        Raises:
            FileNotFoundError: If env_file is provided but does not exist.
            ValidationError: If required environment variables are missing.
        """
        if env_file and not env_file.exists():
            raise FileNotFoundError(f"Environment file not found: {env_file}")

        # Initialize settings with environment file if provided
        env_file_str = str(env_file) if env_file else None
        auth = UniqueAuth(_env_file=env_file_str)  # pyright: ignore[reportCallIssue]
        app = UniqueApp(_env_file=env_file_str)  # pyright: ignore[reportCallIssue]
        api = UniqueApi(_env_file=env_file_str)  # pyright: ignore[reportCallIssue]
        event_filter_options = UniqueChatEventFilterOptions(_env_file=env_file_str)  # pyright: ignore[reportCallIssue]
        return cls(
            auth=auth,
            app=app,
            api=api,
            chat_event_filter_options=event_filter_options,
            env_file=env_file,
        )

    @classmethod
    def from_env_auto(cls, filename: str = "unique.env") -> UniqueSettings:
        """Initialize settings by automatically finding environment file.

        This method will automatically search for an environment file in standard locations
        and fall back to environment variables only if no file is found.

        Args:
            filename: Name of the environment file to search for (default: '.env')

        Returns:
            UniqueSettings instance with values loaded from found env file or environment variables.
        """
        try:
            env_file = find_env_file(filename)
            logger.info(f"Environment file found at {env_file}")
            return cls.from_env(env_file=env_file)
        except EnvFileNotFoundError:
            logger.warning(
                f"Environment file '{filename}' not found. Falling back to environment variables only."
            )
            # Fall back to environment variables only
            return cls.from_env()

    def init_sdk(self) -> None:
        """Initialize the unique_sdk global configuration with these settings.

        This method configures the global unique_sdk module with the API key,
        app ID, and base URL from these settings.
        """
        unique_sdk.api_key = self.app.key.get_secret_value()
        unique_sdk.app_id = self.app.id.get_secret_value()
        unique_sdk.api_base = self.api.sdk_url()

    @classmethod
    def from_env_auto_with_sdk_init(
        cls, filename: str = "unique.env"
    ) -> UniqueSettings:
        """Initialize settings and SDK in one convenient call.

        This method combines from_env_auto() and init_sdk() for the most common use case.

        Args:
            filename: Name of the environment file to search for (default: '.env')

        Returns:
            UniqueSettings instance with SDK already initialized.
        """
        settings = cls.from_env_auto(filename)
        settings.init_sdk()
        return settings

    @classmethod
    def from_chat_event(cls, event: ChatEvent) -> UniqueSettings:
        """Build a :class:`UniqueSettings` from a :class:`ChatEvent`.

        Auth and chat context are extracted from the event.  App and API
        settings are left at their default values; override them via the
        returned instance's properties if needed.

        Args:
            event: The incoming chat event.

        Returns:
            UniqueSettings with auth + chat context populated from the event.
        """
        return cls(
            auth=AuthContext.from_event(event),
            app=UniqueApp(),
            api=UniqueApi(),
            chat=ChatContext.from_chat_event(event),
        )

    @property
    def context(self) -> UniqueContext:
        """The request-level context (auth + optional chat) for this settings object."""
        return self._context

    def update_from_event(self, event: BaseEvent[Any]) -> None:
        self._context = UniqueContext(
            auth=UniqueAuth.from_event(event), chat=self._context.chat
        )

    def with_auth(self, auth: AuthContextProtocol) -> Self:
        """Return a copy of the settings with the new auth context."""
        return self.__class__(
            auth=auth,
            app=self.app,
            api=self.api,
            chat_event_filter_options=self.chat_event_filter_options,
            chat=self._context.chat,
            env_file=self._env_file,
        )

    def with_chat(self, chat: ChatContextProtocol | None) -> Self:
        """Return a copy of the settings with the new chat context.

        Passing ``None`` clears any existing chat context; this mirrors the
        semantics of :meth:`with_auth` and is how MCP request handlers opt out
        of chat scoping when the request does not carry chat identifiers.
        """
        return self.__class__(
            auth=self._context.auth,
            app=self.app,
            api=self.api,
            chat_event_filter_options=self.chat_event_filter_options,
            chat=chat,
            env_file=self._env_file,
        )

    @property
    def api(self) -> UniqueApi:
        return self._env.api

    @property
    def app(self) -> UniqueApp:
        return self._env.app

    @property
    @deprecated("Use authcontext instead")
    def auth(self) -> UniqueAuth:
        if isinstance(self._context.auth, AuthContext):
            return UniqueAuth(
                company_id=SecretStr(self._context.auth.get_confidential_company_id()),
                user_id=SecretStr(self._context.auth.get_confidential_user_id()),
            )
        if not isinstance(self._context.auth, UniqueAuth):
            raise ValueError("Auth context is not a UniqueAuth instance")
        return self._context.auth

    @auth.setter
    @deprecated("Use authcontext instead")
    def auth(self, value: UniqueAuth) -> None:
        self._context.auth = value

    @property
    def authcontext(self) -> AuthContextProtocol:
        return self._context.auth

    @property
    def chat_event_filter_options(self) -> UniqueChatEventFilterOptions | None:
        return self._chat_event_filter_options
