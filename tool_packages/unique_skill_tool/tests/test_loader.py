"""Tests for unique_skill_tool.loader — parse_skill_file and _parse_frontmatter.

Covers:
- _parse_frontmatter: valid frontmatter, YAML exception fallback, non-dict metadata
- parse_skill_file: empty input, missing fields, valid skill, metadata block parsing,
  invalid thinking_level, ValidationError on bad skill name
"""

from __future__ import annotations

from logging import Logger
from unittest.mock import MagicMock

import pytest

from unique_skill_tool.loader import _parse_frontmatter, parse_skill_file
from unique_skill_tool.schemas import SkillDefinition

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_SKILL_MD = """\
---
name: my-skill
description: Does something useful.
---

# My Skill

Here are the instructions.
"""

SKILL_MD_WITH_METADATA = """\
---
name: my-skill
description: Does something useful.
metadata:
  thinking_level: high
---

Instructions here.
"""

SKILL_MD_INVALID_NAME = """\
---
name: Invalid Name With Spaces
description: Has a bad name.
---

Body.
"""


def _make_logger() -> MagicMock:
    return MagicMock(spec=Logger)


# ---------------------------------------------------------------------------
# _parse_frontmatter
# ---------------------------------------------------------------------------


class TestParseFrontmatter:
    @pytest.mark.ai
    def test_valid_frontmatter__returns_metadata_and_body(self) -> None:
        """
        Purpose: Confirm that well-formed YAML frontmatter is parsed correctly.
        Why this matters: All skill loading depends on frontmatter extraction.
        Setup summary: Arrange valid SKILL.md text; assert metadata dict and body
        are returned.
        """
        text = "---\nname: my-skill\ndescription: A skill.\n---\n\nBody text."
        metadata, body = _parse_frontmatter(text=text)

        assert metadata == {"name": "my-skill", "description": "A skill."}
        assert "Body text." in body

    @pytest.mark.ai
    def test_broken_yaml__returns_empty_metadata_and_original_text(self) -> None:
        """
        Purpose: Ensure a YAML parse error never raises; instead falls back to ({}, text).
        Why this matters: A single malformed skill file must not crash the loader.
        Setup summary: Arrange text that triggers a YAML exception; assert graceful fallback.
        """
        broken = "---\n: invalid: yaml: [[\n---\nbody"
        metadata, body = _parse_frontmatter(text=broken)

        assert metadata == {}
        assert body == broken

    @pytest.mark.ai
    def test_non_dict_frontmatter__returns_empty_metadata(self) -> None:
        """
        Purpose: Guard against top-level YAML lists being returned as metadata.
        Why this matters: Non-mapping frontmatter would cause a KeyError downstream.
        Setup summary: Arrange frontmatter whose YAML value is a list; assert ({}, body).
        """
        text = "---\n- item1\n- item2\n---\n\nBody."
        metadata, body = _parse_frontmatter(text=text)

        assert metadata == {}
        assert "Body." in body

    @pytest.mark.ai
    def test_no_frontmatter__returns_empty_metadata_and_full_text_as_body(self) -> None:
        """
        Purpose: Text with no --- delimiters should return empty metadata and the text as body.
        Why this matters: Skills without frontmatter must not be silently corrupted.
        Setup summary: Arrange plain markdown; assert empty dict and text preserved.
        """
        text = "# Just a heading\n\nSome content."
        metadata, body = _parse_frontmatter(text=text)

        assert metadata == {}
        assert "Just a heading" in body


# ---------------------------------------------------------------------------
# parse_skill_file — empty / whitespace input
# ---------------------------------------------------------------------------


class TestParseSkillFileEmpty:
    @pytest.mark.ai
    def test_empty_string__returns_none(self) -> None:
        """
        Purpose: Empty file_text must return None immediately.
        Why this matters: Knowledge-base entries can be empty; loader must not crash.
        Setup summary: Pass ""; assert None.
        """
        result = parse_skill_file(file_text="", content_id="cid")

        assert result is None

    @pytest.mark.ai
    def test_whitespace_only__returns_none(self) -> None:
        """
        Purpose: Whitespace-only file_text counts as empty.
        Why this matters: Same as above; whitespace should not produce a SkillDefinition.
        Setup summary: Pass "   \\n  "; assert None.
        """
        result = parse_skill_file(file_text="   \n  ", content_id="cid")

        assert result is None


# ---------------------------------------------------------------------------
# parse_skill_file — missing required fields
# ---------------------------------------------------------------------------


class TestParseSkillFileMissingFields:
    @pytest.mark.ai
    def test_missing_name__returns_none(self) -> None:
        """
        Purpose: A SKILL.md without a 'name' field is rejected.
        Why this matters: The name is the tool enum value; a missing name is unusable.
        Setup summary: Pass frontmatter without 'name'; assert None.
        """
        text = "---\ndescription: Some description.\n---\n\nBody."
        result = parse_skill_file(file_text=text, content_id="cid")

        assert result is None

    @pytest.mark.ai
    def test_missing_description__returns_none(self) -> None:
        """
        Purpose: A SKILL.md without a 'description' field is rejected.
        Why this matters: The description is shown to the LLM for skill discovery.
        Setup summary: Pass frontmatter without 'description'; assert None.
        """
        text = "---\nname: my-skill\n---\n\nBody."
        result = parse_skill_file(file_text=text, content_id="cid")

        assert result is None

    @pytest.mark.ai
    def test_missing_name_with_logger__emits_warning(self) -> None:
        """
        Purpose: When a logger is provided, a missing-name skip logs a warning.
        Why this matters: Operators must be notified about malformed skill files.
        Setup summary: Pass a mock logger and text without 'name'; assert warning called.
        """
        logger = _make_logger()
        text = "---\ndescription: Some description.\n---\n\nBody."

        result = parse_skill_file(
            file_text=text, content_id="cid", source_label="my/path", logger=logger
        )

        assert result is None
        logger.warning.assert_called_once()
        warning_args = logger.warning.call_args[0]
        assert "my/path" in warning_args[1]

    @pytest.mark.ai
    def test_missing_fields_no_logger__no_error_raised(self) -> None:
        """
        Purpose: logger=None must not cause an AttributeError when fields are missing.
        Why this matters: Callers often omit the logger; silent rejection is correct.
        Setup summary: Pass logger=None and text without name; assert None without exception.
        """
        text = "---\ndescription: desc.\n---\n\nBody."
        result = parse_skill_file(file_text=text, content_id="cid", logger=None)

        assert result is None


# ---------------------------------------------------------------------------
# parse_skill_file — valid skill
# ---------------------------------------------------------------------------


class TestParseSkillFileValid:
    @pytest.mark.ai
    def test_valid_skill__returns_skill_definition(self) -> None:
        """
        Purpose: A well-formed SKILL.md returns a populated SkillDefinition.
        Why this matters: This is the happy path for the entire loader.
        Setup summary: Arrange MINIMAL_SKILL_MD; assert SkillDefinition with correct fields.
        """
        result = parse_skill_file(file_text=MINIMAL_SKILL_MD, content_id="cid-123")

        assert isinstance(result, SkillDefinition)
        assert result.name == "my-skill"
        assert result.description == "Does something useful."
        assert result.content_id == "cid-123"
        assert result.metadata is None

    @pytest.mark.ai
    def test_valid_skill__body_becomes_content(self) -> None:
        """
        Purpose: The markdown body (after frontmatter) is stored as SkillDefinition.content.
        Why this matters: The full instructions must reach the LLM when the skill is invoked.
        Setup summary: Arrange MINIMAL_SKILL_MD; assert body text in result.content.
        """
        result = parse_skill_file(file_text=MINIMAL_SKILL_MD, content_id="cid")

        assert result is not None
        assert "Here are the instructions." in result.content

    @pytest.mark.ai
    def test_no_frontmatter__returns_none(self) -> None:
        """
        Purpose: A file with no frontmatter yields no name/description and is rejected.
        Why this matters: Loader must not produce garbage SkillDefinitions from plain text.
        Setup summary: Pass plain markdown without YAML delimiters; assert None.
        """
        text = "# Plain markdown\n\nNo frontmatter here."
        result = parse_skill_file(file_text=text, content_id="cid")

        assert result is None


# ---------------------------------------------------------------------------
# parse_skill_file — metadata block
# ---------------------------------------------------------------------------


class TestParseSkillFileMetadata:
    @pytest.mark.ai
    def test_valid_thinking_level__sets_skill_meta(self) -> None:
        """
        Purpose: A valid 'thinking_level' in the metadata block is parsed into SkillMetadata.
        Why this matters: The orchestrator uses thinking_level to set reasoning_effort.
        Setup summary: Arrange SKILL_MD_WITH_METADATA (thinking_level: high); assert metadata set.
        """
        result = parse_skill_file(file_text=SKILL_MD_WITH_METADATA, content_id="cid")

        assert result is not None
        assert result.metadata is not None
        assert result.metadata.thinking_level == "high"

    @pytest.mark.ai
    def test_invalid_thinking_level__returns_skill_with_none_thinking_level(
        self,
    ) -> None:
        """
        Purpose: An unrecognised thinking_level value is ignored; skill still loads.
        Why this matters: A typo in one skill file must not break all skill loading.
        Setup summary: Arrange metadata with thinking_level: garbage; assert thinking_level=None.
        """
        text = (
            "---\n"
            "name: my-skill\n"
            "description: Desc.\n"
            "metadata:\n"
            "  thinking_level: garbage\n"
            "---\n\nBody."
        )
        result = parse_skill_file(file_text=text, content_id="cid")

        assert result is not None
        assert result.metadata is not None
        assert result.metadata.thinking_level is None

    @pytest.mark.ai
    def test_invalid_thinking_level_with_logger__emits_warning(self) -> None:
        """
        Purpose: An unrecognised thinking_level logs a warning when logger is provided.
        Why this matters: Operators need visibility into malformed skill metadata.
        Setup summary: Arrange metadata with bad thinking_level and a mock logger; assert warning.
        """
        text = (
            "---\n"
            "name: my-skill\n"
            "description: Desc.\n"
            "metadata:\n"
            "  thinking_level: turbo\n"
            "---\n\nBody."
        )
        logger = _make_logger()

        result = parse_skill_file(
            file_text=text,
            content_id="cid",
            source_label="path/SKILL.md",
            logger=logger,
        )

        assert result is not None
        logger.warning.assert_called_once()
        warning_args = logger.warning.call_args[0]
        assert "path/SKILL.md" in warning_args[1]

    @pytest.mark.ai
    def test_metadata_without_thinking_level__skill_meta_is_set_with_none(self) -> None:
        """
        Purpose: A metadata block that omits thinking_level still produces a SkillMetadata.
        Why this matters: Other metadata keys may be added later; None is a valid default.
        Setup summary: Arrange metadata block with no thinking_level key; assert metadata object.
        """
        text = "---\nname: my-skill\ndescription: Desc.\nmetadata: {}\n---\n\nBody."
        result = parse_skill_file(file_text=text, content_id="cid")

        assert result is not None
        assert result.metadata is not None
        assert result.metadata.thinking_level is None

    @pytest.mark.ai
    def test_non_dict_metadata_block__warns_and_ignores(self) -> None:
        """
        Purpose: A non-mapping 'metadata' value (e.g. a string) is discarded with a warning.
        Why this matters: An accidentally scalar metadata value must not crash the loader.
        Setup summary: Arrange metadata: "not-a-dict"; assert skill loads with metadata=None.
        """
        text = (
            "---\n"
            "name: my-skill\n"
            "description: Desc.\n"
            "metadata: not-a-dict\n"
            "---\n\nBody."
        )
        logger = _make_logger()

        result = parse_skill_file(
            file_text=text, content_id="cid", source_label="some-skill", logger=logger
        )

        assert result is not None
        assert result.metadata is None
        logger.warning.assert_called_once()

    @pytest.mark.ai
    def test_non_dict_metadata_block_no_logger__no_error_raised(self) -> None:
        """
        Purpose: Non-dict metadata with no logger must not raise AttributeError.
        Why this matters: logger=None is the default; non-dict metadata should silently skip.
        Setup summary: Pass metadata: 42 and logger=None; assert skill loads without crash.
        """
        text = "---\nname: my-skill\ndescription: Desc.\nmetadata: 42\n---\n\nBody."
        result = parse_skill_file(file_text=text, content_id="cid", logger=None)

        assert result is not None
        assert result.metadata is None


# ---------------------------------------------------------------------------
# parse_skill_file — ValidationError on bad skill name
# ---------------------------------------------------------------------------


class TestParseSkillFileValidationError:
    @pytest.mark.ai
    def test_invalid_skill_name__returns_none(self) -> None:
        """
        Purpose: A name that fails the kebab-case pattern is rejected by Pydantic validation.
        Why this matters: Invalid names would silently break the OpenAI tool enum.
        Setup summary: Arrange SKILL_MD_INVALID_NAME; assert None returned.
        """
        result = parse_skill_file(file_text=SKILL_MD_INVALID_NAME, content_id="cid")

        assert result is None

    @pytest.mark.ai
    def test_invalid_skill_name_with_logger__emits_warning(self) -> None:
        """
        Purpose: ValidationError on name logs a warning when a logger is provided.
        Why this matters: Operators must know which skill file failed validation.
        Setup summary: Arrange SKILL_MD_INVALID_NAME with mock logger; assert warning with label.
        """
        logger = _make_logger()

        result = parse_skill_file(
            file_text=SKILL_MD_INVALID_NAME,
            content_id="cid",
            source_label="bad-skill/SKILL.md",
            logger=logger,
        )

        assert result is None
        logger.warning.assert_called_once()
        warning_args = logger.warning.call_args[0]
        assert "bad-skill/SKILL.md" in warning_args[1]

    @pytest.mark.ai
    def test_invalid_skill_name_no_logger__no_error_raised(self) -> None:
        """
        Purpose: ValidationError with logger=None must not raise AttributeError.
        Why this matters: Default callers pass no logger; silence is the correct behavior.
        Setup summary: Arrange SKILL_MD_INVALID_NAME with logger=None; assert None, no exception.
        """
        result = parse_skill_file(
            file_text=SKILL_MD_INVALID_NAME, content_id="cid", logger=None
        )

        assert result is None
