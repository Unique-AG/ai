"""Langchain framework utilities."""

try:
    from .client import LangchainNotInstalledError as LangchainNotInstalledError
    from .client import get_langchain_client as get_langchain_client

    __all__ = ["get_langchain_client", "LangchainNotInstalledError"]
except (ImportError, Exception):
    __all__ = []
