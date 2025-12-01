"""Langchain framework utilities."""

try:
    from .client import LangchainNotInstalledError, get_langchain_client

    __all__ = ["get_langchain_client", "LangchainNotInstalledError"]
except (ImportError, Exception):
    # If langchain is not installed, don't export anything
    # This handles both ImportError and LangchainNotInstalledError
    __all__ = []
