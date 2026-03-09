"""Pydantic schemas for skills.

Provides data models for skill metadata (:class:`SkillInfo`,
:class:`SkillVersionInfo`) and the :class:`InlineSkillBundle` used to
embed a skill directly in an API request without prior upload.

The data models are provider-agnostic.  The :meth:`InlineSkillBundle.to_api_dict`
convenience method currently produces OpenAI-format output.
"""

import base64
import io
import zipfile
from pathlib import Path

from pydantic import BaseModel, Field


class SkillInfo(BaseModel):
    """Metadata about a skill."""

    id: str
    name: str
    description: str
    default_version: str
    latest_version: str
    created_at: int


class SkillVersionInfo(BaseModel):
    """Metadata about a specific skill version."""

    skill_id: str
    version: str


class InlineSkillBundle(BaseModel):
    """A ready-to-use inline skill payload for API requests."""

    name: str
    description: str
    base64_zip: str = Field(
        description="Base64-encoded zip archive containing the skill files."
    )

    def to_api_dict(self) -> dict:
        """Convert to the dict format expected by the OpenAI shell tool environment."""
        return {
            "type": "inline",
            "name": self.name,
            "description": self.description,
            "source": {
                "type": "base64",
                "media_type": "application/zip",
                "data": self.base64_zip,
            },
        }

    @classmethod
    def from_directory(
        cls,
        path: str | Path,
        name: str,
        description: str,
    ) -> "InlineSkillBundle":
        """Create an inline skill bundle from a local directory.

        The directory must contain a SKILL.md file at the top level.

        Args:
            path: Path to the skill directory.
            name: Name for the inline skill.
            description: Description of what the skill does.

        Returns:
            An InlineSkillBundle ready for use in the API.

        Raises:
            FileNotFoundError: If the directory or SKILL.md doesn't exist.
        """
        path = Path(path)
        if not path.is_dir():
            raise FileNotFoundError(f"Skill directory not found: {path}")

        skill_md = path / "SKILL.md"
        if not skill_md.exists():
            # Check case-insensitive
            skill_md_candidates = list(path.glob("[Ss][Kk][Ii][Ll][Ll].[Mm][Dd]"))
            if not skill_md_candidates:
                raise FileNotFoundError(
                    f"SKILL.md not found in {path}. Every skill must have a SKILL.md manifest."
                )

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in sorted(path.rglob("*")):
                if file_path.is_file():
                    arcname = str(file_path.relative_to(path.parent))
                    zf.write(file_path, arcname)

        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return cls(name=name, description=description, base64_zip=b64)
