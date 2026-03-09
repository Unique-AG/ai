"""Tests for hosted shell service (tool description building and validation)."""

import pytest

from unique_toolkit.agentic.tools.openai_builtin.base import OpenAIBuiltInToolName
from unique_toolkit.agentic.tools.openai_builtin.hosted_shell.config import (
    InlineSkillConfig,
    OpenAIHostedShellConfig,
    SkillReferenceConfig,
)
from unique_toolkit.agentic.tools.openai_builtin.hosted_shell.service import (
    OpenAIHostedShellTool,
    _build_skills_list,
)


@pytest.mark.ai
def test_hosted_shell_tool__basic_properties__correct_defaults() -> None:
    """
    Purpose: Verify tool name, display name, and default boolean properties.
    Why this matters: Manager routing and UI depend on these properties.
    Setup summary: Construct tool with auto container; assert all basic properties.
    """
    # Arrange
    config = OpenAIHostedShellConfig(use_auto_container=True)
    tool = OpenAIHostedShellTool(config=config, container_id=None)

    # Assert
    assert tool.name == OpenAIBuiltInToolName.HOSTED_SHELL
    assert tool.display_name() == "Hosted Shell"
    assert tool.is_enabled() is True
    assert tool.is_exclusive() is False
    assert tool.takes_control() is False
    prompts = tool.get_tool_prompts()
    assert prompts.name == "shell"
    assert prompts.display_name == "Hosted Shell"


@pytest.mark.ai
def test_hosted_shell_tool__tool_description__returns_shell_type_with_auto_container() -> (
    None
):
    """
    Purpose: Verify tool_description returns correct shape for auto container without skills.
    Why this matters: The API payload must have the right structure.
    Setup summary: Config with use_auto_container=True, no skills; assert shape.
    """
    # Arrange
    config = OpenAIHostedShellConfig(use_auto_container=True)
    tool = OpenAIHostedShellTool(config=config, container_id=None)

    # Act
    desc = tool.tool_description()

    # Assert
    assert desc["type"] == "shell"
    assert desc["environment"]["type"] == "container_auto"
    assert "skills" not in desc["environment"]


@pytest.mark.ai
def test_hosted_shell_tool__tool_description__includes_skill_references() -> None:
    """
    Purpose: Verify skill references are included in the environment.
    Why this matters: Skills must be passed through to the API.
    Setup summary: Config with one skill reference; assert skills list in environment.
    """
    # Arrange
    config = OpenAIHostedShellConfig(
        use_auto_container=True,
        skill_references=[SkillReferenceConfig(skill_id="skill_abc", version="2")],
    )
    tool = OpenAIHostedShellTool(config=config, container_id=None)

    # Act
    desc = tool.tool_description()

    # Assert
    skills = desc["environment"]["skills"]
    assert len(skills) == 1
    assert skills[0]["type"] == "skill_reference"
    assert skills[0]["skill_id"] == "skill_abc"
    assert skills[0]["version"] == "2"


@pytest.mark.ai
def test_hosted_shell_tool__tool_description__includes_inline_skills() -> None:
    """
    Purpose: Verify inline skills are included in the environment.
    Why this matters: Inline skills must carry name, description, and source.
    Setup summary: Config with one inline skill; assert skills list shape.
    """
    # Arrange
    config = OpenAIHostedShellConfig(
        use_auto_container=True,
        inline_skills=[
            InlineSkillConfig(
                name="test-skill",
                description="A test skill",
                base64_zip="dGVzdA==",
            )
        ],
    )
    tool = OpenAIHostedShellTool(config=config, container_id=None)

    # Act
    desc = tool.tool_description()

    # Assert
    skills = desc["environment"]["skills"]
    assert len(skills) == 1
    assert skills[0]["type"] == "inline"
    assert skills[0]["name"] == "test-skill"
    assert skills[0]["description"] == "A test skill"
    assert skills[0]["source"]["type"] == "base64"
    assert skills[0]["source"]["media_type"] == "application/zip"
    assert skills[0]["source"]["data"] == "dGVzdA=="


@pytest.mark.ai
def test_hosted_shell_tool__tool_description__uses_container_reference_when_not_auto() -> (
    None
):
    """
    Purpose: Verify tool_description uses container_reference when use_auto_container is False.
    Why this matters: Persistent containers must pass the container_id.
    Setup summary: Config with use_auto_container=False and a container_id.
    """
    # Arrange
    config = OpenAIHostedShellConfig(use_auto_container=False)
    tool = OpenAIHostedShellTool(config=config, container_id="cntr_xyz")

    # Act
    desc = tool.tool_description()

    # Assert
    assert desc["type"] == "shell"
    assert desc["environment"]["type"] == "container_reference"
    assert desc["environment"]["container_id"] == "cntr_xyz"
    assert "skills" not in desc["environment"]


@pytest.mark.ai
def test_hosted_shell_tool__tool_description__container_reference_excludes_skills_even_when_configured() -> (
    None
):
    """
    Purpose: Verify skills are NOT included when using container_reference, even if configured.
    Why this matters: The OpenAI API rejects skills inside container_reference environments.
    Setup summary: Config with skills + use_auto_container=False; assert skills absent.
    """
    # Arrange
    config = OpenAIHostedShellConfig(
        use_auto_container=False,
        skill_references=[SkillReferenceConfig(skill_id="skill_abc", version="2")],
        inline_skills=[
            InlineSkillConfig(
                name="test-skill",
                description="A test skill",
                base64_zip="dGVzdA==",
            )
        ],
    )
    tool = OpenAIHostedShellTool(config=config, container_id="cntr_xyz")

    # Act
    desc = tool.tool_description()

    # Assert
    assert desc["environment"]["type"] == "container_reference"
    assert "skills" not in desc["environment"]


@pytest.mark.ai
def test_hosted_shell_tool__raises__when_no_container_id_and_not_auto() -> None:
    """
    Purpose: Verify ValueError when container_id is None and use_auto_container is False.
    Why this matters: Prevents runtime failures from missing container.
    Setup summary: Construct with no container_id and use_auto_container=False.
    """
    # Arrange
    config = OpenAIHostedShellConfig(use_auto_container=False)

    # Act & Assert
    with pytest.raises(ValueError, match="container_id"):
        OpenAIHostedShellTool(config=config, container_id=None)


@pytest.mark.ai
def test_hosted_shell_tool__tool_description__combines_refs_and_inline_skills() -> None:
    """
    Purpose: Verify both skill references and inline skills appear in the same environment.
    Why this matters: Users can mix pre-uploaded and inline skills.
    Setup summary: Config with one of each; assert both in skills list.
    """
    # Arrange
    config = OpenAIHostedShellConfig(
        use_auto_container=True,
        skill_references=[SkillReferenceConfig(skill_id="skill_1")],
        inline_skills=[
            InlineSkillConfig(
                name="inline-1",
                description="Inline skill",
                base64_zip="dGVzdA==",
            )
        ],
    )
    tool = OpenAIHostedShellTool(config=config, container_id=None)

    # Act
    desc = tool.tool_description()

    # Assert
    skills = desc["environment"]["skills"]
    assert len(skills) == 2
    assert skills[0]["type"] == "skill_reference"
    assert skills[1]["type"] == "inline"


@pytest.mark.ai
def test_hosted_shell_tool__is_exclusive__respects_constructor_arg() -> None:
    """
    Purpose: Verify is_exclusive returns the value passed at construction.
    Why this matters: Exclusive tools prevent other tools from being selected.
    Setup summary: Construct with is_exclusive=True; assert is_exclusive.
    """
    # Arrange
    config = OpenAIHostedShellConfig(use_auto_container=True)
    tool = OpenAIHostedShellTool(config=config, container_id=None, is_exclusive=True)

    # Assert
    assert tool.is_exclusive() is True


@pytest.mark.ai
def test_build_skills_list__returns_empty__when_no_skills() -> None:
    """
    Purpose: Verify _build_skills_list returns empty list when no skills configured.
    Why this matters: Environment should not have a skills key when empty.
    Setup summary: Config with no skills; assert empty list.
    """
    # Arrange
    config = OpenAIHostedShellConfig()

    # Act
    skills = _build_skills_list(config)

    # Assert
    assert skills == []


@pytest.mark.ai
def test_build_skills_list__omits_version_when_none() -> None:
    """
    Purpose: Verify skill reference omits version key when version is None.
    Why this matters: The API uses the default version when version is not specified.
    Setup summary: Skill reference with version=None; assert 'version' not in dict.
    """
    # Arrange
    config = OpenAIHostedShellConfig(
        skill_references=[SkillReferenceConfig(skill_id="skill_abc")]
    )

    # Act
    skills = _build_skills_list(config)

    # Assert
    assert len(skills) == 1
    assert "version" not in skills[0]
    assert skills[0]["skill_id"] == "skill_abc"


@pytest.mark.ai
def test_hosted_shell_tool__tool_description__includes_file_ids_in_auto_container() -> None:
    """
    Purpose: Verify file_ids are included in the container_auto environment.
    Why this matters: Files must be passed via file_ids for auto containers.
    Setup summary: Construct with file_ids; assert file_ids in environment.
    """
    # Arrange
    config = OpenAIHostedShellConfig(use_auto_container=True)
    tool = OpenAIHostedShellTool(config=config, container_id=None, file_ids=["file-abc", "file-def"])

    # Act
    desc = tool.tool_description()

    # Assert
    assert desc["environment"]["type"] == "container_auto"
    assert desc["environment"]["file_ids"] == ["file-abc", "file-def"]


@pytest.mark.ai
def test_hosted_shell_tool__tool_description__omits_file_ids_when_empty() -> None:
    """
    Purpose: Verify file_ids key is absent when no files are provided.
    Why this matters: Clean API payloads should not include empty arrays.
    Setup summary: Construct with no file_ids; assert file_ids not in environment.
    """
    # Arrange
    config = OpenAIHostedShellConfig(use_auto_container=True)
    tool = OpenAIHostedShellTool(config=config, container_id=None)

    # Act
    desc = tool.tool_description()

    # Assert
    assert desc["environment"]["type"] == "container_auto"
    assert "file_ids" not in desc["environment"]
