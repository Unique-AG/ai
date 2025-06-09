"""HTTP Client factory with static client registry."""

import importlib
from enum import StrEnum
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ConfigDict, Field

from unique_client.core.http_clients.protocol import HTTPClientProtocol


class HTTPClientType(StrEnum):
    """Available HTTP client types."""

    REQUESTS = "requests"
    HTTPX = "httpx"


class ClientInfo(BaseModel):
    """Information about an HTTP client implementation with validation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: HTTPClientType = Field(..., description="Unique name for the HTTP client")
    module_name: str = Field(
        ..., description="Full Python module path for the client implementation"
    )
    class_name: str = Field(..., description="Class name within the module")
    dependencies: List[str] = Field(
        ..., description="List of required Python packages", min_length=1
    )


# Static registry of available HTTP client implementations
CLIENT_REGISTRY: Dict[HTTPClientType, ClientInfo] = {
    HTTPClientType.REQUESTS: ClientInfo(
        name=HTTPClientType.REQUESTS,
        module_name="unique_client.core.http_clients.requests_client",
        class_name="RequestsClient",
        dependencies=["requests"],
    ),
    HTTPClientType.HTTPX: ClientInfo(
        name=HTTPClientType.HTTPX,
        module_name="unique_client.core.http_clients.httpx_client",
        class_name="HTTPXClient",
        dependencies=["httpx", "anyio"],
    ),
}


def _check_dependencies(dependencies: List[str]) -> bool:
    """Check if all required dependencies are available."""
    for dep in dependencies:
        try:
            importlib.import_module(dep)
        except ImportError:
            return False
    return True


def _get_client_class(client_info: ClientInfo) -> Optional[Type[HTTPClientProtocol]]:
    """Dynamically import and return a client class."""
    try:
        module = importlib.import_module(client_info.module_name)
        return getattr(module, client_info.class_name)
    except (ImportError, AttributeError):
        return None


def _create_client_with_dependency_check(
    client_info: ClientInfo, *args: Any, **kwargs: Any
) -> HTTPClientProtocol:
    """Create a client instance after checking dependencies."""
    # Check dependencies first
    if not _check_dependencies(client_info.dependencies):
        missing_deps = [
            dep for dep in client_info.dependencies if not _check_dependencies([dep])
        ]
        raise ImportError(
            f"Client '{client_info.name.value}' requires missing dependencies: {missing_deps}"
        )

    # Get the client class
    client_class = _get_client_class(client_info)
    if not client_class:
        raise ImportError(
            f"Failed to import client class {client_info.class_name} from {client_info.module_name}"
        )

    # Create and return the client instance
    return client_class(*args, **kwargs)


def get_available_clients() -> List[str]:
    """Get list of available HTTP client names based on installed dependencies."""
    available: list[str] = []
    for client_info in CLIENT_REGISTRY.values():
        if _check_dependencies(client_info.dependencies):
            available.append(client_info.name.value)
    return available


def get_default_client(*args: Any, **kwargs: Any) -> HTTPClientProtocol:
    """Get the default HTTP client (requests with async fallback)."""
    # Try to get requests client first
    if HTTPClientType.REQUESTS in CLIENT_REGISTRY:
        try:
            # Try to add async fallback (without passing requests-specific args)
            async_client = get_async_client()
            if async_client:
                kwargs["async_fallback_client"] = async_client
            return _create_client_with_dependency_check(
                CLIENT_REGISTRY[HTTPClientType.REQUESTS], *args, **kwargs
            )
        except ImportError:
            pass  # Fall through to try other clients

    # Fallback to any available client
    return get_any_client(*args, **kwargs)


def get_async_client(*args: Any, **kwargs: Any) -> Optional[HTTPClientProtocol]:
    """Get an async-capable HTTP client."""
    # Filter out RequestsClient-specific arguments for async clients
    async_kwargs = {
        k: v for k, v in kwargs.items() if k not in ["async_fallback_client", "session"]
    }

    # Prefer httpx for async operations
    if HTTPClientType.HTTPX in CLIENT_REGISTRY:
        try:
            return _create_client_with_dependency_check(
                CLIENT_REGISTRY[HTTPClientType.HTTPX], *args, **async_kwargs
            )
        except ImportError:
            pass  # Dependencies not available

    # Add other async clients here as they're implemented
    return None


def get_any_client(*args: Any, **kwargs: Any) -> HTTPClientProtocol:
    """Get any available HTTP client."""
    for client_info in CLIENT_REGISTRY.values():
        try:
            return _create_client_with_dependency_check(client_info, *args, **kwargs)
        except ImportError:
            continue  # Try next client

    # If no clients are available, raise an error
    raise ImportError(
        f"No HTTP client libraries found. Please install one of: {[c.dependencies for c in CLIENT_REGISTRY.values()]}"
    )


def get_client_by_name(name: str, *args: Any, **kwargs: Any) -> HTTPClientProtocol:
    """Get a specific HTTP client by name."""
    for client_info in CLIENT_REGISTRY.values():
        if client_info.name.value == name:
            return _create_client_with_dependency_check(client_info, *args, **kwargs)

    raise ValueError(
        f"Unknown client name: {name}. Available clients: {list(HTTPClientType)}"
    )


def get_client_by_type(
    client_type: HTTPClientType, *args: Any, **kwargs: Any
) -> HTTPClientProtocol:
    """Get a specific HTTP client by type (type-safe version)."""
    if client_type not in CLIENT_REGISTRY:
        raise ValueError(
            f"Unknown client type: {client_type}. Available types: {list(CLIENT_REGISTRY.keys())}"
        )

    client_info = CLIENT_REGISTRY[client_type]
    return _create_client_with_dependency_check(client_info, *args, **kwargs)
