import pytest

from unique_web_search.services.content_processing.cleaning.character_sanitize import (
    CharacterSanitize,
)


@pytest.fixture
def sanitizer():
    return CharacterSanitize(enabled=True)


@pytest.fixture
def disabled_sanitizer():
    return CharacterSanitize(enabled=False)


class TestCharacterSanitize:
    def test_strips_null_bytes(self, sanitizer: CharacterSanitize):
        assert sanitizer("hello\x00world") == "helloworld"

    def test_strips_multiple_null_bytes(self, sanitizer: CharacterSanitize):
        assert sanitizer("\x00\x00data\x00") == "data"

    def test_strips_c0_control_characters(self, sanitizer: CharacterSanitize):
        assert sanitizer("a\x01b\x02c\x03d\x08e\x0ef\x1fg") == "abcdefg"

    def test_preserves_tab(self, sanitizer: CharacterSanitize):
        assert sanitizer("col1\tcol2") == "col1\tcol2"

    def test_preserves_newline(self, sanitizer: CharacterSanitize):
        assert sanitizer("line1\nline2") == "line1\nline2"

    def test_preserves_carriage_return(self, sanitizer: CharacterSanitize):
        assert sanitizer("line1\r\nline2") == "line1\r\nline2"

    def test_strips_del_character(self, sanitizer: CharacterSanitize):
        assert sanitizer("abc\x7fdef") == "abcdef"

    def test_strips_c1_control_characters(self, sanitizer: CharacterSanitize):
        assert sanitizer("a\x80b\x8fc\x9fd") == "abcd"

    def test_strips_unicode_replacement_character(self, sanitizer: CharacterSanitize):
        assert sanitizer("hello\ufffdworld") == "helloworld"

    def test_strips_unicode_noncharacters(self, sanitizer: CharacterSanitize):
        assert sanitizer("a\ufffeb\uffffc") == "abc"

    def test_preserves_normal_text(self, sanitizer: CharacterSanitize):
        text = "Hello, world! This is a normal sentence."
        assert sanitizer(text) == text

    def test_preserves_unicode_text(self, sanitizer: CharacterSanitize):
        text = "Héllo wörld 你好 🌍"
        assert sanitizer(text) == text

    def test_preserves_markdown(self, sanitizer: CharacterSanitize):
        text = "# Heading\n\n- item 1\n- item 2\n\n**bold** and *italic*"
        assert sanitizer(text) == text

    def test_empty_string(self, sanitizer: CharacterSanitize):
        assert sanitizer("") == ""

    def test_only_control_chars(self, sanitizer: CharacterSanitize):
        assert sanitizer("\x00\x01\x02\x7f\x80") == ""

    def test_mixed_valid_and_invalid(self, sanitizer: CharacterSanitize):
        text = "Hello\x00 World\x01!\x7f Good\x80 Morning\ufffd."
        assert sanitizer(text) == "Hello World! Good Morning."

    def test_disabled_returns_content_unchanged(
        self, disabled_sanitizer: CharacterSanitize
    ):
        text = "hello\x00world"
        assert disabled_sanitizer(text) == text

    def test_is_enabled_property(self):
        assert CharacterSanitize(enabled=True).is_enabled is True
        assert CharacterSanitize(enabled=False).is_enabled is False
