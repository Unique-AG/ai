import re

_CONTROL_CHAR_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f\ufffe\uffff\ufffd]"
)


class CharacterSanitize:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def __call__(self, content: str) -> str:
        if self.enabled:
            return _CONTROL_CHAR_RE.sub("", content)
        return content

    @property
    def is_enabled(self) -> bool:
        return self.enabled
