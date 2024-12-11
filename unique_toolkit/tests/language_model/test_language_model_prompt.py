import pytest

from unique_toolkit.language_model.prompt import Prompt
from unique_toolkit.language_model.schemas import (
    LanguageModelSystemMessage,
    LanguageModelUserMessage,
)


def test_prompt_initialization():
    template = "Hello, $name!"
    prompt = Prompt(template, name="World")
    assert prompt.template.template == template
    assert prompt.content == "Hello, World!"


def test_prompt_format():
    prompt = Prompt("Hello, $name!")
    formatted = prompt.format(name="Alice")
    assert formatted == "Hello, Alice!"
    assert prompt.content == "Hello, Alice!"


def test_prompt_format_multiple_variables():
    prompt = Prompt("$greeting $name! How is the $time?")
    formatted = prompt.format(greeting="Hello", name="Bob", time="morning")
    assert formatted == "Hello Bob! How is the morning?"


def test_prompt_format_missing_variable():
    prompt = Prompt("Hello, $name!")
    with pytest.raises(KeyError):
        prompt.format()


def test_prompt_to_user_msg():
    prompt = Prompt("Hello, $name!", name="World")
    user_msg = prompt.to_user_msg()
    assert isinstance(user_msg, LanguageModelUserMessage)
    assert user_msg.content == "Hello, World!"


def test_prompt_to_system_msg():
    prompt = Prompt("System instruction: $instruction", instruction="Be helpful")
    system_msg = prompt.to_system_msg()
    assert isinstance(system_msg, LanguageModelSystemMessage)
    assert system_msg.content == "System instruction: Be helpful"
