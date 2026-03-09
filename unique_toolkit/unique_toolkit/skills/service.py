import base64
import io
import logging
import zipfile
from pathlib import Path

from openai import AsyncOpenAI

from unique_toolkit.skills.schemas import InlineSkillBundle, SkillInfo, SkillVersionInfo

logger = logging.getLogger(__name__)


class SkillService:
    """Standalone service for managing OpenAI Skills.

    This service is independent of any specific tool and can be used
    to manage skills for hosted shells, other agents (e.g. Claude Code),
    or any consumer that supports the OpenAI Skills API.

    Usage:
        client = AsyncOpenAI()
        service = SkillService(client)

        # Create a skill from a local directory
        skill = await service.create_skill_from_directory("./my_skill")

        # Or create from a zip file
        skill = await service.create_skill_from_zip("./my_skill.zip")

        # List all skills
        skills = await service.list_skills()

        # Create a new version
        version = await service.create_version("skill_abc123", "./my_skill_v2")

        # Build an inline skill bundle (no upload needed)
        bundle = service.build_inline_skill("./my_skill", "analyzer", "Analyzes data")
    """

    def __init__(self, client: AsyncOpenAI):
        self._client = client

    async def create_skill_from_directory(
        self,
        path: str | Path,
    ) -> SkillInfo:
        """Create a new skill by uploading a directory.

        The directory must contain a SKILL.md manifest file.

        Args:
            path: Path to the skill directory.

        Returns:
            SkillInfo with the created skill metadata.
        """
        path = Path(path)
        if not path.is_dir():
            raise FileNotFoundError(f"Skill directory not found: {path}")

        zip_bytes = _zip_directory(path)
        return await self._create_skill_from_bytes(zip_bytes)

    async def create_skill_from_zip(
        self,
        path: str | Path,
    ) -> SkillInfo:
        """Create a new skill by uploading a zip file.

        Args:
            path: Path to the zip file.

        Returns:
            SkillInfo with the created skill metadata.
        """
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"Zip file not found: {path}")

        zip_bytes = path.read_bytes()
        return await self._create_skill_from_bytes(zip_bytes)

    async def get_skill(self, skill_id: str) -> SkillInfo:
        """Retrieve metadata for a skill.

        Args:
            skill_id: The ID of the skill.

        Returns:
            SkillInfo with the skill metadata.
        """
        skill = await self._client.skills.retrieve(skill_id)
        return SkillInfo(
            id=skill.id,
            name=skill.name,
            description=skill.description,
            default_version=skill.default_version,
            latest_version=skill.latest_version,
            created_at=skill.created_at,
        )

    async def list_skills(self) -> list[SkillInfo]:
        """List all skills.

        Returns:
            List of SkillInfo objects.
        """
        skills_page = await self._client.skills.list()
        return [
            SkillInfo(
                id=skill.id,
                name=skill.name,
                description=skill.description,
                default_version=skill.default_version,
                latest_version=skill.latest_version,
                created_at=skill.created_at,
            )
            for skill in skills_page.data
        ]

    async def delete_skill(self, skill_id: str) -> None:
        """Delete a skill.

        Args:
            skill_id: The ID of the skill to delete.
        """
        await self._client.skills.delete(skill_id)
        logger.info("Deleted skill %s", skill_id)

    async def create_version(
        self,
        skill_id: str,
        path: str | Path,
    ) -> SkillVersionInfo:
        """Create a new version of an existing skill.

        Args:
            skill_id: The ID of the skill to version.
            path: Path to the skill directory for the new version.

        Returns:
            SkillVersionInfo with the new version metadata.
        """
        path = Path(path)
        if not path.is_dir():
            raise FileNotFoundError(f"Skill directory not found: {path}")

        zip_bytes = _zip_directory(path)
        buf = io.BytesIO(zip_bytes)
        buf.name = "skill.zip"

        version = await self._client.skills.versions.create(
            skill_id=skill_id,
            files=[buf],
        )
        logger.info(
            "Created version %s for skill %s", version.version, skill_id
        )
        return SkillVersionInfo(skill_id=skill_id, version=version.version)

    async def set_default_version(
        self, skill_id: str, version: str
    ) -> SkillInfo:
        """Set the default version for a skill.

        Args:
            skill_id: The ID of the skill.
            version: The version number to set as default.

        Returns:
            Updated SkillInfo.
        """
        skill = await self._client.skills.update(
            skill_id=skill_id,
            default_version=version,
        )
        logger.info("Set default version %s for skill %s", version, skill_id)
        return SkillInfo(
            id=skill.id,
            name=skill.name,
            description=skill.description,
            default_version=skill.default_version,
            latest_version=skill.latest_version,
            created_at=skill.created_at,
        )

    @staticmethod
    def build_inline_skill(
        path: str | Path,
        name: str,
        description: str,
    ) -> InlineSkillBundle:
        """Build an inline skill bundle from a local directory.

        This does NOT upload to the Skills API. Instead, it creates
        a base64-encoded zip that can be embedded directly in an API request.

        Args:
            path: Path to the skill directory.
            name: Name for the inline skill.
            description: Description of what the skill does.

        Returns:
            An InlineSkillBundle ready for use.
        """
        return InlineSkillBundle.from_directory(
            path=path, name=name, description=description
        )

    async def _create_skill_from_bytes(self, zip_bytes: bytes) -> SkillInfo:
        """Upload a zip archive as a new skill."""
        buf = io.BytesIO(zip_bytes)
        buf.name = "skill.zip"

        skill = await self._client.skills.create(files=[buf])
        logger.info("Created skill %s (%s)", skill.name, skill.id)
        return SkillInfo(
            id=skill.id,
            name=skill.name,
            description=skill.description,
            default_version=skill.default_version,
            latest_version=skill.latest_version,
            created_at=skill.created_at,
        )


def _zip_directory(path: Path) -> bytes:
    """Zip a directory into bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(path.rglob("*")):
            if file_path.is_file():
                arcname = str(file_path.relative_to(path.parent))
                zf.write(file_path, arcname)
    return buf.getvalue()
