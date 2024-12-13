from string import Template
from typing import Any

from unique_toolkit.language_model.schemas import (
    LanguageModelSystemMessage,
    LanguageModelUserMessage,
)


class Prompt:
    """
    A class for handling templated prompts that can be formatted into LanguageModelSystemMessage and LanguageModelUserMessage.

    This class wraps a string template and provides methods to format it with variables and
    convert it into different types of language model messages. It uses Python's string.Template
    for variable substitution.

    Usage:
        # Create a prompt with a template and set variables
        prompt = Prompt("Hello, ${name}!", name="World")

        # Substitute the template with variables and return the formatted content
        content = prompt.substitute(name="World")

        # Get the formatted content
        content = prompt.content  # Returns "Hello, World!"

        # Get the template
        template = prompt.template

        # Convert to language model messages
        system_msg = prompt.to_system_msg()
        user_msg = prompt.to_user_msg()
        user_msg_with_images = prompt.to_user_msg_with_images(images=["IMAGE_IN_BASE64"])

    Properties:
        template: Returns the underlying template string
        content: Returns the current formatted content string

    Methods:
        substitute(**kwargs): Substitutes the template with the given variables
        to_user_msg(): Converts the prompt to a LanguageModelUserMessage
        to_user_msg_with_images(images): Converts the prompt to a LanguageModelUserMessage with images
    """

    def __init__(self, template: str, **kwargs):
        self._template = Template(template)
        self._content = self._template.template
        if kwargs:
            self._content = self._template.substitute(**kwargs)

    @property
    def template(self):
        """
        Returns the template string.

        Returns:
            str: The template string.
        """
        return self._template

    @property
    def content(self):
        """
        Returns the formatted content string.

        Returns:
            str: The formatted content string.
        """
        return self._content

    def substitute(self, **kwargs: Any) -> str:
        """
        Substitutes the template with the given kwargs. Raises KeyError if a required parameter is missing.

        Args:
            **kwargs: Keyword arguments to substitute into the template.

        Returns:
            str: The substituted template string.

        Raises:
            KeyError: If a required parameter in the template is missing from kwargs.
        """
        self._content = self._template.substitute(**kwargs)
        return self._content

    def to_system_msg(self) -> LanguageModelSystemMessage:
        """
        Returns a LanguageModelSystemMessage with the content of the prompt.

        Returns:
            LanguageModelSystemMessage: The formatted prompt.
        """
        return LanguageModelSystemMessage(content=self._content)

    def to_user_msg(self) -> LanguageModelUserMessage:
        """
        Returns a LanguageModelUserMessage with the content of the prompt.

        Returns:
            LanguageModelUserMessage: The formatted prompt.
        """
        return LanguageModelUserMessage(content=self._content)

    def to_user_msg_with_images(self, images: list[str]) -> LanguageModelUserMessage:
        """
        Returns a LanguageModelUserMessage with the content of the prompt and the images.

        Args:
            images: List of images in base64 format.

        Returns:
            LanguageModelUserMessage: The formatted prompt with images.
        """
        return LanguageModelUserMessage(
            content=[
                {"type": "text", "text": self._content},
                *[
                    {"type": "image_url", "imageUrl": {"url": image}}
                    for image in images
                ],
            ]
        )
