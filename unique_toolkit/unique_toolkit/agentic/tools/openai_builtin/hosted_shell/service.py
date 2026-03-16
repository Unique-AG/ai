"""OpenAI Hosted Shell tool implementation.

Provides :class:`OpenAIHostedShellTool`, a built-in tool that gives an
OpenAI model access to a sandboxed shell environment with optional
pre-configured *skills*.  Two environment modes are supported:

* **container_auto** — ephemeral container managed by the API.  Supports
  both ``skill_reference`` (pre-uploaded) and ``inline`` (base64-zip) skills.
  Files are passed via the ``file_ids`` field in the environment dict.
* **container_reference** — persistent container created and reused across
  turns.  Skills are **not** supported; files are uploaded directly to the
  container.

The ``gpt-5.2`` model (or newer) is required by the OpenAI Responses API
for the ``shell`` tool type with ``environment``; bare ``shell`` works on
``gpt-5.1``+.
"""

import base64
import io
import logging
import re
import zipfile
from typing import Any, override

from openai import AsyncOpenAI

from unique_toolkit import ContentService
from unique_toolkit.agentic.tools.openai_builtin.base import (
    FunctionShellToolParam,
    OpenAIBuiltInTool,
    OpenAIBuiltInToolName,
)
from unique_toolkit.agentic.tools.openai_builtin.container_utils import (
    ContainerShortTermMemorySchema,
    create_container_if_not_exists,
    get_container_memory_manager,
    upload_files_to_container,
)
from unique_toolkit.agentic.tools.openai_builtin.hosted_shell.config import (
    InlineSkillConfig,
    OpenAIHostedShellConfig,
)
from unique_toolkit.agentic.tools.schemas import ToolPrompts
from unique_toolkit.content.functions import download_content_to_bytes_async
from unique_toolkit.content.schemas import Content

logger = logging.getLogger(__name__)

_MEMORY_NAME = "container_hosted_shell"
_CONTAINER_NAME_PREFIX = "hosted_shell"


async def _upload_files_for_auto_container(
    client: AsyncOpenAI,
    uploaded_files: list[Content],
    memory: ContainerShortTermMemorySchema,
    content_service: ContentService,
    chat_id: str,
    files_client: AsyncOpenAI | None = None,
) -> ContainerShortTermMemorySchema:
    """Upload files via client.files.create for use with container_auto's file_ids.

    Args:
        files_client: Optional direct OpenAI client for the Files API,
            bypassing the proxy.  Falls back to *client* when ``None``.
    """
    # Use the direct client for the Files API when available (needed for
    # LiteLLM models where the proxy doesn't support /v1/files).
    upload_client = files_client or client

    memory = memory.model_copy(deep=True)

    for file in uploaded_files:
        if file.id in memory.file_ids:
            logger.info("File with id %s already uploaded (cached)", file.id)
            continue

        logger.info("Uploading file %s via files API for auto container", file.id)
        file_content = await content_service.download_content_to_bytes_async(
            content_id=file.id, chat_id=chat_id
        )

        openai_file = await upload_client.files.create(
            file=(file.key, file_content),
            purpose="assistants",
        )
        memory.file_ids[file.id] = openai_file.id

    return memory


def _parse_skill_front_matter(skill_md_content: str) -> tuple[str, str]:
    """Extract ``name`` and ``description`` from a SKILL.md's YAML front matter.

    The front matter is delimited by ``---`` lines at the top of the file.
    Uses simple regex parsing to avoid a hard dependency on PyYAML.

    Returns:
        A ``(name, description)`` tuple.

    Raises:
        ValueError: If the front matter or required fields are missing.
    """
    match = re.match(r"^---\s*\n(.*?)\n---", skill_md_content, re.DOTALL)
    if not match:
        raise ValueError("SKILL.md is missing YAML front matter (--- delimiters)")

    front_matter = match.group(1)

    name_match = re.search(r'^name:\s*["\']?([^"\'\n]+)["\']?\s*$', front_matter, re.MULTILINE)
    desc_match = re.search(r'^description:\s*["\']?([^"\'\n]+)["\']?\s*$', front_matter, re.MULTILINE)

    if not name_match:
        raise ValueError("SKILL.md front matter is missing 'name' field")
    if not desc_match:
        raise ValueError("SKILL.md front matter is missing 'description' field")

    return name_match.group(1).strip().strip("\"'"), desc_match.group(1).strip().strip("\"'")


def _extract_skill_from_zip(zip_bytes: bytes) -> InlineSkillConfig:
    """Read a skill zip, extract name/description from SKILL.md, return an InlineSkillConfig."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        # Find SKILL.md (case-insensitive, may be nested one level)
        skill_md_path = None
        for name in zf.namelist():
            if name.lower().endswith("skill.md"):
                skill_md_path = name
                break

        if skill_md_path is None:
            raise ValueError(
                f"Skill zip does not contain a SKILL.md file. "
                f"Found: {zf.namelist()[:10]}"
            )

        skill_md_content = zf.read(skill_md_path).decode("utf-8")

    name, description = _parse_skill_front_matter(skill_md_content)
    b64 = base64.b64encode(zip_bytes).decode("ascii")

    return InlineSkillConfig(name=name, description=description, base64_zip=b64)


async def _resolve_knowledge_base_skills(
    content_ids: list[str],
    user_id: str,
    company_id: str,
) -> list[InlineSkillConfig]:
    """Download skill zips from the knowledge base and convert to inline skills.

    For each content ID, downloads the zip file, reads the SKILL.md front
    matter to extract the name and description (so they always match), and
    returns a list of :class:`InlineSkillConfig` ready for the API.
    """
    skills: list[InlineSkillConfig] = []

    for content_id in content_ids:
        logger.info("Downloading skill zip from knowledge base: %s", content_id)
        zip_bytes = await download_content_to_bytes_async(
            user_id=user_id,
            company_id=company_id,
            content_id=content_id,
            chat_id=None,
        )

        try:
            skill = _extract_skill_from_zip(zip_bytes)
            logger.info("Resolved KB skill: name=%s, zip_size=%d", skill.name, len(zip_bytes))
            skills.append(skill)
        except Exception:
            logger.exception("Failed to parse skill zip for content_id=%s", content_id)
            raise

    return skills


def _build_skills_list(config: OpenAIHostedShellConfig) -> list[dict[str, Any]]:
    """Build the skills list for the ``container_auto`` shell environment.

    Merges both ``skill_references`` (pre-uploaded) and ``inline_skills``
    (base64-zip bundles) from the config into a single list of dicts
    suitable for the ``environment.skills`` field.
    """
    skills: list[dict[str, Any]] = []

    for skill_ref in config.skill_references:
        skill_entry: dict[str, Any] = {
            "type": "skill_reference",
            "skill_id": skill_ref.skill_id,
        }
        if skill_ref.version is not None:
            skill_entry["version"] = skill_ref.version
        skills.append(skill_entry)

    for inline_skill in config.inline_skills:
        skills.append(
            {
                "type": "inline",
                "name": inline_skill.name,
                "description": inline_skill.description,
                "source": {
                    "type": "base64",
                    "media_type": "application/zip",
                    "data": inline_skill.base64_zip,
                },
            }
        )

    return skills


class OpenAIHostedShellTool(OpenAIBuiltInTool[FunctionShellToolParam]):
    """Built-in tool that exposes a sandboxed shell to the model.

    The tool description returned by :meth:`tool_description` is a
    ``FunctionShellToolParam`` dict that can be passed directly to the
    OpenAI Responses API ``tools`` parameter.

    Use :meth:`build_tool` (async factory) in the Unique platform to
    handle file uploads and container management automatically, or
    instantiate directly for standalone / script usage.
    """

    DISPLAY_NAME = "Hosted Shell"

    def __init__(
        self,
        config: OpenAIHostedShellConfig,
        container_id: str | None,
        is_exclusive: bool = False,
        file_ids: list[str] | None = None,
    ) -> None:
        self._config = config

        if not config.use_auto_container and container_id is None:
            raise ValueError("`container_id` required when not using `auto` containers")

        self._container_id = container_id
        self._is_exclusive = is_exclusive
        self._file_ids = file_ids or []

    @property
    @override
    def name(self) -> OpenAIBuiltInToolName:
        return OpenAIBuiltInToolName.HOSTED_SHELL

    @override
    def tool_description(self) -> FunctionShellToolParam:
        if self._config.use_auto_container:
            environment: dict[str, Any] = {"type": "container_auto"}
            skills = _build_skills_list(self._config)
            if skills:
                environment["skills"] = skills
            if self._file_ids:
                environment["file_ids"] = self._file_ids
            return {"type": "shell", "environment": environment}  # type: ignore

        # Skills are NOT supported with container_reference — the API rejects them.
        environment = {
            "type": "container_reference",
            "container_id": self._container_id,
        }
        return {"type": "shell", "environment": environment}  # type: ignore

    @override
    def is_enabled(self) -> bool:
        return True

    @override
    def takes_control(self) -> bool:
        return False

    @override
    def is_exclusive(self) -> bool:
        return self._is_exclusive

    @classmethod
    async def build_tool(
        cls,
        config: OpenAIHostedShellConfig,
        uploaded_files: list[Content],
        client: AsyncOpenAI,
        content_service: ContentService,
        company_id: str,
        user_id: str,
        chat_id: str,
        is_exclusive: bool = False,
        files_client: AsyncOpenAI | None = None,
    ) -> "OpenAIHostedShellTool":
        """Async factory that creates the tool with file uploads and container management.

        Handles two modes based on ``config.use_auto_container``:

        * **auto** — uploads chat files via the OpenAI Files API and passes
          their IDs through ``file_ids`` in the environment dict.
        * **persistent** — creates/reuses a container and uploads files
          directly into it.

        Args:
            config: Shell tool configuration.
            uploaded_files: Files attached to the current chat.
            client: An ``AsyncOpenAI`` client instance.
            content_service: Service for downloading file bytes from the platform.
            company_id: Unique company identifier.
            user_id: Unique user identifier.
            chat_id: Unique chat identifier.
            is_exclusive: If ``True``, this tool is the only one available.

        Returns:
            A fully configured :class:`OpenAIHostedShellTool`.
        """
        # Resolve knowledge-base skill zips into inline skills
        if config.skill_content_ids:
            kb_skills = await _resolve_knowledge_base_skills(
                content_ids=config.skill_content_ids,
                user_id=user_id,
                company_id=company_id,
            )
            # Merge into the config's inline_skills (non-destructive copy)
            config = config.model_copy(
                update={"inline_skills": [*config.inline_skills, *kb_skills]}
            )

        if config.use_auto_container:
            logger.info("Using `container_auto` environment setting for hosted shell")

            file_ids: list[str] = []
            if config.upload_files_in_chat_to_container and uploaded_files:
                memory_manager = get_container_memory_manager(
                    company_id=company_id,
                    user_id=user_id,
                    chat_id=chat_id,
                    memory_name=_MEMORY_NAME,
                )
                memory = await memory_manager.load_async()
                if memory is None:
                    memory = ContainerShortTermMemorySchema()

                memory = await _upload_files_for_auto_container(
                    client=client,
                    uploaded_files=uploaded_files,
                    memory=memory,
                    content_service=content_service,
                    chat_id=chat_id,
                    files_client=files_client,
                )

                await memory_manager.save_async(memory)
                file_ids = list(memory.file_ids.values())

            return cls(
                config=config,
                container_id=None,
                is_exclusive=is_exclusive,
                file_ids=file_ids,
            )

        memory_manager = get_container_memory_manager(
            company_id=company_id,
            user_id=user_id,
            chat_id=chat_id,
            memory_name=_MEMORY_NAME,
        )

        memory = await memory_manager.load_async()

        memory = await create_container_if_not_exists(
            client=client,
            memory=memory,
            chat_id=chat_id,
            user_id=user_id,
            company_id=company_id,
            expires_after_minutes=config.expires_after_minutes,
            container_name_prefix=_CONTAINER_NAME_PREFIX,
            files_client=files_client,
        )

        if config.upload_files_in_chat_to_container:
            memory = await upload_files_to_container(
                client=client,
                uploaded_files=uploaded_files,
                content_service=content_service,
                chat_id=chat_id,
                memory=memory,
                files_client=files_client,
            )

        await memory_manager.save_async(memory)

        assert memory.container_id is not None

        return OpenAIHostedShellTool(
            config=config, container_id=memory.container_id, is_exclusive=is_exclusive
        )

    @override
    def get_tool_prompts(self) -> ToolPrompts:
        return ToolPrompts(
            name="shell",
            display_name=self.DISPLAY_NAME,
            tool_description=self._config.tool_description,
            tool_system_prompt=self._config.tool_description_for_system_prompt,
            tool_format_information_for_system_prompt="",
            tool_user_prompt=self._config.tool_description_for_user_prompt,
            tool_format_information_for_user_prompt="",
            input_model={},
        )

    @override
    def display_name(self) -> str:
        return self.DISPLAY_NAME
