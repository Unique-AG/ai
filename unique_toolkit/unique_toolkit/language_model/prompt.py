from string import Template
from typing import Any

from unique_toolkit.language_model.schemas import (
    LanguageModelSystemMessage,
    LanguageModelUserMessage,
)


class Prompt:
    def __init__(self, template: str, **kwargs):
        self._template = Template(template)
        self._content = self._template.template
        if kwargs:
            self._content = self._template.substitute(**kwargs)

    @property
    def template(self):
        return self._template

    @property
    def content(self):
        return self._content

    def format(self, **kwargs: Any) -> str:
        """
        Formats the template with the given kwargs. Raises KeyError if a required parameter is missing.

        Args:
            **kwargs: Keyword arguments to substitute into the template.

        Returns:
            str: The formatted template string.

        Raises:
            KeyError: If a required parameter in the template is missing from kwargs.
        """
        self._content = self._template.substitute(**kwargs)
        return self._content

    def to_user_msg(self) -> LanguageModelUserMessage:
        return LanguageModelUserMessage(content=self._content)

    def to_system_msg(self) -> LanguageModelSystemMessage:
        return LanguageModelSystemMessage(content=self._content)
