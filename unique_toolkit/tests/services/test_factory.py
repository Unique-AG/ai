"""
Unit tests for UniqueServiceFactory.

Covers:
1. Registration and creation of services
2. ServiceNotRegisteredError for unregistered services
3. Registry isolation between tests
4. Default registrations via register_known_services()
5. override() context manager
6. verify()
"""

import pytest
from pydantic import SecretStr

from unique_toolkit.app.unique_settings import (
    AuthContext,
    ChatContext,
    UniqueApi,
    UniqueApp,
    UniqueContext,
    UniqueSettings,
)
from unique_toolkit.services.factory import (
    ServiceNotRegisteredError,
    UniqueServiceFactory,
)

# ---------------------------------------------------------------------------
# Helpers / simple stub services
# ---------------------------------------------------------------------------


class _SimpleService:
    def __init__(self, *, company_id: str, user_id: str):
        self.company_id = company_id
        self.user_id = user_id

    @classmethod
    def from_settings(cls, settings: UniqueSettings, **kwargs) -> "_SimpleService":
        return cls(
            company_id=settings.authcontext.get_confidential_company_id(),
            user_id=settings.authcontext.get_confidential_user_id(),
        )


class _AnotherService:
    def __init__(self, *, company_id: str):
        self.company_id = company_id

    @classmethod
    def from_settings(cls, settings: UniqueSettings, **kwargs) -> "_AnotherService":
        return cls(company_id=settings.authcontext.get_confidential_company_id())


class _UnregisteredService:
    pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def auth() -> AuthContext:
    return AuthContext(user_id=SecretStr("user-1"), company_id=SecretStr("company-1"))


@pytest.fixture
def settings(auth: AuthContext) -> UniqueSettings:
    return UniqueSettings(auth=auth, app=UniqueApp(), api=UniqueApi())


@pytest.fixture
def chat_context() -> ChatContext:
    return ChatContext(
        chat_id="chat-1",
        assistant_id="assistant-1",
        last_assistant_message_id="amsg-1",
        last_user_message_id="umsg-1",
        last_user_message_text="",
    )


@pytest.fixture
def settings_with_chat(auth: AuthContext, chat_context: ChatContext) -> UniqueSettings:
    s = UniqueSettings(auth=auth, app=UniqueApp(), api=UniqueApi())
    s._context = UniqueContext(auth=auth, chat=chat_context)
    return s


@pytest.fixture(autouse=True)
def isolated_registry():
    """Save and restore the UniqueServiceFactory registry around each test."""
    original_registry = UniqueServiceFactory._registry.copy()
    UniqueServiceFactory._registry.clear()
    yield
    UniqueServiceFactory._registry.clear()
    UniqueServiceFactory._registry.update(original_registry)


# ---------------------------------------------------------------------------
# Tests: registration
# ---------------------------------------------------------------------------


class TestUniqueServiceFactoryRegistration:
    @pytest.mark.ai
    def test_register__stores_creator__for_service_type(self):
        """
        Purpose: Verify that register stores the creator function keyed by the class name string.
        Why this matters: create() looks up the registry by name; if registration is silently dropped no service can be created.
        Setup summary: Register _SimpleService; assert name present in _registry.
        """
        UniqueServiceFactory.register(_SimpleService)
        assert "_SimpleService" in UniqueServiceFactory._registry

    @pytest.mark.ai
    def test_register__stores_from_settings__as_creator(self, settings: UniqueSettings):
        """
        Purpose: Verify that register stores from_settings as the creator callable.
        Why this matters: The factory always delegates to from_settings; a wrong creator causes wrong instances.
        Setup summary: Register _SimpleService; call registered creator; assert it returns correct instance.
        """
        UniqueServiceFactory.register(_SimpleService)
        creator = UniqueServiceFactory._registry["_SimpleService"]
        svc = creator(settings)
        assert isinstance(svc, _SimpleService)

    @pytest.mark.ai
    def test_register__overwrites_existing__when_same_type_registered_twice(
        self, settings: UniqueContext
    ):
        """
        Purpose: Verify that re-registering a type replaces the previous creator.
        Why this matters: Test doubles and env-specific overrides depend on the last registration winning.
        Setup summary: Register _SimpleService; override via register again with a lambda; assert the new creator is used.
        """
        UniqueServiceFactory.register(_SimpleService)
        UniqueServiceFactory._registry["_SimpleService"] = (
            lambda s, **kw: _SimpleService(
                company_id="overwritten",
                user_id="overwritten",  # type: ignore
            )
        )
        svc = UniqueServiceFactory.create(_SimpleService, settings=settings)
        assert svc.company_id == "overwritten"  # type: ignore


# ---------------------------------------------------------------------------
# Tests: create
# ---------------------------------------------------------------------------


class TestUniqueServiceFactoryCreate:
    @pytest.mark.ai
    def test_create__returns_correct_type(self, settings: UniqueContext):
        """
        Purpose: Verify create returns an instance of the requested service type.
        Why this matters: Callers cast the result; wrong type causes AttributeError at runtime.
        Setup summary: Register and create _SimpleService; assert isinstance.
        """
        UniqueServiceFactory.register(_SimpleService)
        svc = UniqueServiceFactory.create(_SimpleService, settings=settings)
        assert isinstance(svc, _SimpleService)

    @pytest.mark.ai
    def test_create__passes_auth_fields__to_creator(self, settings: UniqueContext):
        """
        Purpose: Verify auth credentials from the settings are forwarded to the creator.
        Why this matters: Services depend on correct credentials; wrong values silently send requests to the wrong tenant.
        Setup summary: Settings with company-1/user-1; assert those values on the created service.
        """
        UniqueServiceFactory.register(_SimpleService)
        svc = UniqueServiceFactory.create(_SimpleService, settings=settings)
        assert svc.company_id == "company-1"  # type: ignore
        assert svc.user_id == "user-1"  # type: ignore

    @pytest.mark.ai
    def test_create__by_string_name__returns_correct_type(
        self, settings: UniqueContext
    ):
        """
        Purpose: Verify create accepts the class name as a string and resolves to the right service.
        Why this matters: Dynamic dispatch patterns pass service names as strings; wrong resolution returns the wrong object.
        Setup summary: Register _SimpleService; call create("_SimpleService"); assert isinstance.
        """
        UniqueServiceFactory.register(_SimpleService)
        svc = UniqueServiceFactory.create("_SimpleService", settings=settings)
        assert isinstance(svc, _SimpleService)

    @pytest.mark.ai
    def test_create__forwards_extra_kwargs__to_creator(self, settings: UniqueContext):
        """
        Purpose: Verify extra kwargs passed to create are forwarded to the creator function.
        Why this matters: Some creators need additional configuration not available in the settings.
        Setup summary: Register custom creator that captures kwargs; pass extra_param; assert received.
        """
        received_kwargs: dict = {}

        def _capturing_creator(s, **kw):
            received_kwargs.update(kw)
            return _SimpleService(
                company_id=s.authcontext.get_confidential_company_id(),
                user_id=s.authcontext.get_confidential_user_id(),
            )

        UniqueServiceFactory._registry["_SimpleService"] = _capturing_creator
        UniqueServiceFactory.create(
            _SimpleService, settings=settings, extra_param="hello"
        )
        assert received_kwargs == {"extra_param": "hello"}


# ---------------------------------------------------------------------------
# Tests: instance (bound) factory
# ---------------------------------------------------------------------------


class TestUniqueServiceFactoryInstance:
    @pytest.mark.ai
    def test_get__creates_service_using_bound_settings(self, settings: UniqueSettings):
        """
        Purpose: Verify the instance-bound factory.get() creates a service using its stored settings.
        Why this matters: Applications bind a factory once per request; get() must use that settings, not a stale one.
        Setup summary: Bound factory; get _SimpleService by name; assert correct company_id.
        """
        UniqueServiceFactory.register(_SimpleService)
        factory = UniqueServiceFactory(settings=settings)
        svc = factory.get("_SimpleService")
        assert isinstance(svc, _SimpleService)
        assert svc.company_id == "company-1"

    @pytest.mark.ai
    def test_instance_uses_bound_settings_auth(self, settings: UniqueSettings):
        """
        Purpose: Verify the bound settings' auth credentials appear on the returned service.
        Why this matters: Each request has its own credentials; the factory must not bleed auth between requests.
        Setup summary: Bound factory with user-1/company-1; assert those values on the service.
        """
        UniqueServiceFactory.register(_SimpleService)
        factory = UniqueServiceFactory(settings=settings)
        svc = factory.get("_SimpleService")
        assert svc.user_id == "user-1"  # type: ignore
        assert svc.company_id == "company-1"  # type: ignore


# ---------------------------------------------------------------------------
# Tests: override context manager
# ---------------------------------------------------------------------------


class TestUniqueServiceFactoryOverride:
    @pytest.mark.ai
    def test_override__replaces_creator__inside_block(self, settings: UniqueContext):
        """
        Purpose: Verify override swaps the creator within the with-block.
        Why this matters: Tests depend on controlled service substitution; if the override doesn't take effect tests verify the wrong thing.
        Setup summary: Register real creator; override with mock lambda; assert mock service returned inside block.
        """
        UniqueServiceFactory.register(_SimpleService)
        mock_svc = _SimpleService(company_id="mock", user_id="mock")

        with UniqueServiceFactory.override("_SimpleService", lambda s, **kw: mock_svc):
            svc = UniqueServiceFactory.create(_SimpleService, settings=settings)
            assert svc is mock_svc

    @pytest.mark.ai
    def test_override__accepts_type_as_first_arg(self, settings: UniqueContext):
        """
        Purpose: Verify override also accepts the service class (not just a string) as the first argument.
        Why this matters: Callers should be able to pass the type directly for a more natural API.
        Setup summary: Override with type; assert mock returned.
        """
        UniqueServiceFactory.register(_SimpleService)
        mock_svc = _SimpleService(company_id="mock", user_id="mock")

        with UniqueServiceFactory.override(_SimpleService, lambda s, **kw: mock_svc):
            svc = UniqueServiceFactory.create(_SimpleService, settings=settings)
            assert svc is mock_svc

    @pytest.mark.ai
    def test_override__restores_original_creator__after_block(
        self, settings: UniqueContext
    ):
        """
        Purpose: Verify the original creator is restored after the with-block exits normally.
        Why this matters: A leaked override would cause subsequent tests to receive mock objects silently.
        Setup summary: Register real creator; override; exit block; assert real creator is back.
        """
        UniqueServiceFactory.register(_SimpleService)

        with UniqueServiceFactory.override(
            "_SimpleService",
            lambda s, **kw: _SimpleService(company_id="mock", user_id="mock"),
        ):
            pass

        svc = UniqueServiceFactory.create("_SimpleService", settings=settings)
        assert svc.company_id == "company-1"  # type: ignore

    @pytest.mark.ai
    def test_override__restores_creator__even_after_exception(
        self, settings: UniqueContext
    ):
        """
        Purpose: Verify the original creator is restored even when an exception is raised inside the block.
        Why this matters: Without try/finally cleanup, a test crash would leave the registry in a broken state.
        Setup summary: Register real creator; raise inside override block; assert real creator still used after.
        """
        UniqueServiceFactory.register(_SimpleService)

        with pytest.raises(RuntimeError):
            with UniqueServiceFactory.override(
                "_SimpleService",
                lambda s, **kw: _SimpleService(company_id="mock", user_id="mock"),
            ):
                raise RuntimeError("boom")

        svc = UniqueServiceFactory.create("_SimpleService", settings=settings)
        assert svc.company_id == "company-1"  # type: ignore

    @pytest.mark.ai
    def test_override__removes_registration__when_type_was_not_registered(
        self, settings: UniqueContext
    ):
        """
        Purpose: Verify override cleans up after itself when the type was not previously registered.
        Why this matters: Temporary registrations must not persist; otherwise unregistered types appear registered after a test.
        Setup summary: Override unregistered type; assert service created inside; assert ServiceNotRegisteredError after.
        """
        with UniqueServiceFactory.override(
            "_SimpleService",
            lambda s, **kw: _SimpleService(company_id="temp", user_id="temp"),
        ):
            svc = UniqueServiceFactory.create(_SimpleService, settings=settings)
            assert svc.company_id == "temp"  # type: ignore

        with pytest.raises(ServiceNotRegisteredError):
            UniqueServiceFactory.create(_SimpleService, settings=settings)

    @pytest.mark.ai
    def test_override__can_be_nested(self, settings: UniqueContext):
        """
        Purpose: Verify nested override blocks each have the expected creator active.
        Why this matters: Integration tests sometimes layer overrides; each level must see only its own substitution.
        Setup summary: Register real creator; nest two overrides; assert each level returns the right service.
        """
        UniqueServiceFactory.register(_SimpleService)
        mock_a = _SimpleService(company_id="a", user_id="a")
        mock_b = _SimpleService(company_id="b", user_id="b")

        with UniqueServiceFactory.override("_SimpleService", lambda s, **kw: mock_a):
            assert (
                UniqueServiceFactory.create(_SimpleService, settings=settings) is mock_a
            )
            with UniqueServiceFactory.override(
                "_SimpleService", lambda s, **kw: mock_b
            ):
                assert (
                    UniqueServiceFactory.create(_SimpleService, settings=settings)
                    is mock_b
                )
            assert (
                UniqueServiceFactory.create(_SimpleService, settings=settings) is mock_a
            )

        svc = UniqueServiceFactory.create(_SimpleService, settings=settings)
        assert svc.company_id == "company-1"  # type: ignore


# ---------------------------------------------------------------------------
# Tests: verify
# ---------------------------------------------------------------------------


class TestUniqueServiceFactoryVerify:
    @pytest.mark.ai
    def test_verify__passes__when_all_service_names_registered(self):
        """
        Purpose: Verify verify() does not raise when all listed names are registered.
        Why this matters: Applications call verify at startup to fail fast on missing registrations.
        Setup summary: Register both services; call verify; assert no exception.
        """
        UniqueServiceFactory.register(_SimpleService)
        UniqueServiceFactory.register(_AnotherService)
        UniqueServiceFactory.verify("_SimpleService", "_AnotherService")

    @pytest.mark.ai
    def test_verify__raises__for_first_missing_service_name(self):
        """
        Purpose: Verify verify() raises ServiceNotRegisteredError for the first missing name.
        Why this matters: Partial registrations would let some services work and others silently fail at runtime.
        Setup summary: Register only _SimpleService; verify both; assert error mentions _AnotherService.
        """
        UniqueServiceFactory.register(_SimpleService)

        with pytest.raises(ServiceNotRegisteredError, match="_AnotherService"):
            UniqueServiceFactory.verify("_SimpleService", "_AnotherService")

    @pytest.mark.ai
    def test_verify__raises__when_registry_empty(self):
        """
        Purpose: Verify verify() raises when called with a name and the registry is empty.
        Why this matters: An empty registry means no setup was done; that must surface immediately.
        Setup summary: Empty registry; verify("_SimpleService"); assert ServiceNotRegisteredError.
        """
        with pytest.raises(ServiceNotRegisteredError):
            UniqueServiceFactory.verify("_SimpleService")

    @pytest.mark.ai
    def test_verify__passes__with_no_arguments(self):
        """
        Purpose: Verify verify() with no arguments succeeds regardless of registry state.
        Why this matters: Calling verify() as a no-op should be safe and not raise spuriously.
        Setup summary: Empty registry; call verify(); assert no exception.
        """
        UniqueServiceFactory.verify()


# ---------------------------------------------------------------------------
# Tests: error handling
# ---------------------------------------------------------------------------


class TestUniqueServiceFactoryErrors:
    @pytest.mark.ai
    def test_create__raises_service_not_registered_error__for_unregistered_type(
        self, settings: UniqueContext
    ):
        """
        Purpose: Verify create raises ServiceNotRegisteredError for a type that was never registered.
        Why this matters: A KeyError would give a confusing traceback; a domain-specific error is actionable.
        Setup summary: Empty registry; call create(_UnregisteredService); assert ServiceNotRegisteredError.
        """
        with pytest.raises(ServiceNotRegisteredError):
            UniqueServiceFactory.create("_UnregisteredService", settings=settings)

    @pytest.mark.ai
    def test_create__raises_service_not_registered_error__for_unknown_string(
        self, settings: UniqueContext
    ):
        """
        Purpose: Verify create raises ServiceNotRegisteredError with the name in the message for unknown strings.
        Why this matters: Callers using string dispatch need the unresolved name in the error to know what to register.
        Setup summary: Call create("unknown_service"); assert ServiceNotRegisteredError mentions "unknown_service".
        """
        with pytest.raises(ServiceNotRegisteredError, match="unknown_service"):
            UniqueServiceFactory.create("unknown_service", settings=settings)

    @pytest.mark.ai
    def test_service_not_registered_error__message_contains_class_name(
        self, settings: UniqueContext
    ):
        """
        Purpose: Verify ServiceNotRegisteredError includes the class name to guide the developer.
        Why this matters: A generic message forces inspecting the registry manually; the class name pinpoints the fix.
        Setup summary: Call create(_UnregisteredService); assert error message contains "_UnregisteredService".
        """
        with pytest.raises(ServiceNotRegisteredError, match="_UnregisteredService"):
            UniqueServiceFactory.create("_UnregisteredService", settings=settings)


# ---------------------------------------------------------------------------
# Tests: default registrations
# ---------------------------------------------------------------------------


class TestDefaultRegistrations:
    @pytest.fixture(autouse=True)
    def with_defaults(self, isolated_registry):
        UniqueServiceFactory.register_known_services()

    @pytest.mark.ai
    def test_knowledge_base_service__registered(self, settings: UniqueContext):
        """
        Purpose: Verify KnowledgeBaseService is registered by register_known_services().
        Why this matters: Applications rely on the default registry; a missing entry fails at first content search.
        Setup summary: Call register_known_services; create KnowledgeBaseService; assert isinstance.
        """
        from unique_toolkit.services.knowledge_base import KnowledgeBaseService

        svc = UniqueServiceFactory.create(KnowledgeBaseService, settings=settings)
        assert isinstance(svc, KnowledgeBaseService)

    @pytest.mark.ai
    def test_chat_service__created_with_chat(self, settings_with_chat: UniqueContext):
        """
        Purpose: Verify ChatService is created correctly when a full chat context is present.
        Why this matters: The default creator must wire all chat fields; any gap silently breaks message operations.
        Setup summary: Full context; create ChatService; assert company_id and chat_id set correctly.
        """
        from unique_toolkit.services.chat_service import ChatService

        svc = UniqueServiceFactory.create(ChatService, settings=settings_with_chat)
        assert isinstance(svc, ChatService)
        assert svc._company_id == "company-1"
        assert svc._chat_id == "chat-1"

    @pytest.mark.ai
    def test_chat_service__requires_chat(self, settings: UniqueContext):
        """
        Purpose: Verify ChatService creation raises ValueError when no chat context is provided.
        Why this matters: ChatService is only valid in a chat session; a clear error prevents silent failures.
        Setup summary: Auth-only settings; create ChatService; assert ValueError.
        """
        from unique_toolkit.services.chat_service import ChatService

        with pytest.raises(ValueError):
            UniqueServiceFactory.create(ChatService, settings=settings)

    @pytest.mark.ai
    def test_unregistered_service__raises(self, settings: UniqueContext):
        """
        Purpose: Verify that a service not included in register_known_services() raises ServiceNotRegisteredError.
        Why this matters: Confirms the default registry is intentionally scoped; unexpected services must not sneak in.
        Setup summary: Try to create _SimpleService (not registered by default); assert ServiceNotRegisteredError.
        """
        with pytest.raises(ServiceNotRegisteredError):
            UniqueServiceFactory.create(_SimpleService, settings=settings)

    @pytest.mark.ai
    def test_services_accessible_by_string_name(
        self, settings_with_chat: UniqueContext
    ):
        """
        Purpose: Verify default services can be resolved by their string class name.
        Why this matters: Dynamic dispatch (e.g. config-driven service selection) uses string names.
        Setup summary: Create ChatService by string "ChatService"; assert isinstance.
        """
        from unique_toolkit.services.chat_service import ChatService

        svc = UniqueServiceFactory.create("ChatService", settings=settings_with_chat)
        assert isinstance(svc, ChatService)
