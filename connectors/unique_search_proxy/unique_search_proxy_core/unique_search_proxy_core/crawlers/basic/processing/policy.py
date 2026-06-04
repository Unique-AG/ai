from enum import StrEnum


class ContentTypeHandlerPolicy(StrEnum):
    """Whether the basic crawler may run the built-in processor for a media type."""

    ALLOW = "allow"
    FORBID = "forbid"


DEFAULT_HTML_HANDLERS: dict[str, ContentTypeHandlerPolicy] = {
    "text/html": ContentTypeHandlerPolicy.ALLOW,
    "application/xhtml+xml": ContentTypeHandlerPolicy.ALLOW,
}
