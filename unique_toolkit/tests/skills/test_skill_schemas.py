"""Tests for skill schemas (InlineSkillBundle, SkillInfo, SkillVersionInfo)."""

import base64
import os
import tempfile
import zipfile

import pytest

from unique_toolkit.skills.schemas import InlineSkillBundle, SkillInfo, SkillVersionInfo


@pytest.mark.ai
def test_skill_info__stores_all_fields() -> None:
    """
    Purpose: Verify SkillInfo correctly stores all metadata fields.
    Why this matters: Skill info is used for display and version management.
    Setup summary: Construct with explicit values; assert all fields.
    """
    # Act
    info = SkillInfo(
        id="skill_abc",
        name="data-analyzer",
        description="Analyzes data",
        default_version="1",
        latest_version="3",
        created_at=1700000000,
    )

    # Assert
    assert info.id == "skill_abc"
    assert info.name == "data-analyzer"
    assert info.description == "Analyzes data"
    assert info.default_version == "1"
    assert info.latest_version == "3"
    assert info.created_at == 1700000000


@pytest.mark.ai
def test_skill_version_info__stores_fields() -> None:
    """
    Purpose: Verify SkillVersionInfo correctly stores skill_id and version.
    Why this matters: Used to track created versions.
    Setup summary: Construct with explicit values; assert fields.
    """
    # Act
    info = SkillVersionInfo(skill_id="skill_abc", version="2")

    # Assert
    assert info.skill_id == "skill_abc"
    assert info.version == "2"


@pytest.mark.ai
def test_inline_skill_bundle__to_api_dict__returns_correct_shape() -> None:
    """
    Purpose: Verify to_api_dict returns the shape expected by the OpenAI API.
    Why this matters: Inline skills must match the API contract.
    Setup summary: Construct bundle; assert dict shape and values.
    """
    # Arrange
    bundle = InlineSkillBundle(
        name="test-skill",
        description="A test skill",
        base64_zip="dGVzdA==",
    )

    # Act
    result = bundle.to_api_dict()

    # Assert
    assert result["type"] == "inline"
    assert result["name"] == "test-skill"
    assert result["description"] == "A test skill"
    assert result["source"]["type"] == "base64"
    assert result["source"]["media_type"] == "application/zip"
    assert result["source"]["data"] == "dGVzdA=="


@pytest.mark.ai
def test_inline_skill_bundle__from_directory__creates_valid_zip() -> None:
    """
    Purpose: Verify from_directory creates a valid base64-encoded zip with SKILL.md.
    Why this matters: The bundle must be a valid zip that OpenAI can extract.
    Setup summary: Create temp dir with SKILL.md and a script; assert zip contents.
    """
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = os.path.join(tmpdir, "my_skill")
        os.makedirs(skill_dir)

        with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
            f.write("---\nname: test\ndescription: A test skill\n---\nInstructions here.")

        with open(os.path.join(skill_dir, "script.py"), "w") as f:
            f.write("print('hello')")

        # Act
        bundle = InlineSkillBundle.from_directory(
            path=skill_dir,
            name="my-skill",
            description="My test skill",
        )

    # Assert
    assert bundle.name == "my-skill"
    assert bundle.description == "My test skill"

    # Verify the base64 decodes to a valid zip
    zip_bytes = base64.b64decode(bundle.base64_zip)
    import io

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        assert any("SKILL.md" in n for n in names)
        assert any("script.py" in n for n in names)


@pytest.mark.ai
def test_inline_skill_bundle__from_directory__raises_when_dir_missing() -> None:
    """
    Purpose: Verify FileNotFoundError when directory doesn't exist.
    Why this matters: Clear error on misconfiguration.
    Setup summary: Pass non-existent path; assert FileNotFoundError.
    """
    # Act & Assert
    with pytest.raises(FileNotFoundError, match="not found"):
        InlineSkillBundle.from_directory(
            path="/nonexistent/skill_dir",
            name="test",
            description="test",
        )


@pytest.mark.ai
def test_inline_skill_bundle__from_directory__raises_when_skill_md_missing() -> None:
    """
    Purpose: Verify FileNotFoundError when SKILL.md is missing from directory.
    Why this matters: Every skill must have a SKILL.md manifest.
    Setup summary: Create temp dir without SKILL.md; assert FileNotFoundError.
    """
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = os.path.join(tmpdir, "no_manifest")
        os.makedirs(skill_dir)
        with open(os.path.join(skill_dir, "script.py"), "w") as f:
            f.write("print('no manifest')")

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="SKILL.md"):
            InlineSkillBundle.from_directory(
                path=skill_dir,
                name="test",
                description="test",
            )
