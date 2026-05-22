from unique_web_search.services.text_sanitize import strip_controls


class CharacterSanitize:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def __call__(self, content: str) -> str:
        if self.enabled:
            return strip_controls(content)
        return content

    @property
    def is_enabled(self) -> bool:
        return self.enabled
