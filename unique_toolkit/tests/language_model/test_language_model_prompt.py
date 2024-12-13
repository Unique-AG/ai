import pytest

from unique_toolkit.language_model.prompt import Prompt
from unique_toolkit.language_model.schemas import (
    LanguageModelSystemMessage,
    LanguageModelUserMessage,
)


def test_prompt_initialization():
    template = "Hello, $name $world!"
    prompt = Prompt(template, world="Earth", name="World")
    assert prompt.template.template == template
    assert prompt.content == "Hello, World Earth!"


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
    prompt = Prompt("System instruction: ${instruction}", instruction="Be helpful")
    system_msg = prompt.to_system_msg()
    assert isinstance(system_msg, LanguageModelSystemMessage)
    assert system_msg.content == "System instruction: Be helpful"


def test_prompt_to_user_msg_with_images():
    prompt = Prompt("Check out these images, $name!", name="Alice")
    images = ["data:image/jpeg;base64,abc123", "data:image/png;base64,xyz789"]
    user_msg = prompt.to_user_msg_with_images(images)

    assert isinstance(user_msg, LanguageModelUserMessage)
    assert isinstance(user_msg.content, list)
    assert len(user_msg.content) == 3  # 1 text + 2 images

    # Check text content
    assert user_msg.content[0] == {
        "type": "text",
        "text": "Check out these images, Alice!",
    }

    # Check image contents
    for i, image in enumerate(images):
        assert user_msg.content[i + 1] == {
            "type": "image_url",
            "imageUrl": {"url": image},
        }
