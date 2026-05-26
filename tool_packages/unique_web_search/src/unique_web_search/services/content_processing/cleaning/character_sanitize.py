from unique_web_search.services.text_sanitize import strip_controls


class CharacterSanitize:
    """Drop ASCII control characters from page content.

    Thin wrapper around :func:`strip_controls` so the content-processing
    pipeline shares the same regex / character class as the boundary
    sanitization on :class:`WebSearchResult`. See ``services/text_sanitize.py``
    for the rationale (Postgres NUL-byte rejection, etc.).
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def __call__(self, content: str) -> str:
        if self.enabled:
            return strip_controls(content)
        return content

    @property
    def is_enabled(self) -> bool:
        return self.enabled
