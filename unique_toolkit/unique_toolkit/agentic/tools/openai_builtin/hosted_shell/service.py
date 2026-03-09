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

The ``gpt-5.4`` model (or newer) is currently required by the OpenAI
Responses API for the ``shell`` tool type.
"""

import logging
from typing import Any, override

from openai import AsyncOpenAI, BaseModel, NotFoundError

try:
    from openai.types.responses.tool_param import FunctionShellToolParam
except ImportError:
    FunctionShellToolParam = dict[str, Any]  # type: ignore[assignment, misc]

from unique_toolkit import ContentService, ShortTermMemoryService
from unique_toolkit.agentic.short_term_memory_manager.persistent_short_term_memory_manager import (
    PersistentShortMemoryManager,
)
from unique_toolkit.agentic.tools.openai_builtin.base import (
    OpenAIBuiltInTool,
    OpenAIBuiltInToolName,
)
from unique_toolkit.agentic.tools.openai_builtin.hosted_shell.config import (
    OpenAIHostedShellConfig,
)
from unique_toolkit.agentic.tools.schemas import ToolPrompts
from unique_toolkit.content.schemas import Content

logger = logging.getLogger(__name__)

_SHORT_TERM_MEMORY_NAME = "container_hosted_shell"


class HostedShellShortTermMemorySchema(BaseModel):
    """Short-term memory persisted between turns for the hosted shell.

    Attributes:
        container_id: ID of the persistent container (``None`` when using
            ``container_auto``).
        file_ids: Mapping of Unique platform content IDs to OpenAI file IDs
            so that files are only uploaded once per chat session.
    """

    container_id: str | None = None
    file_ids: dict[str, str] = {}  # Mapping of unique file id to openai file id


HostedShellMemoryManager = PersistentShortMemoryManager[
    HostedShellShortTermMemorySchema
]


def _get_hosted_shell_short_term_memory_manager(
    company_id: str, user_id: str, chat_id: str
) -> HostedShellMemoryManager:
    """Create a memory manager scoped to the current chat session."""
    short_term_memory_service = ShortTermMemoryService(
        company_id=company_id,
        user_id=user_id,
        chat_id=chat_id,
        message_id=None,
    )
    short_term_memory_manager = PersistentShortMemoryManager(
        short_term_memory_service=short_term_memory_service,
        short_term_memory_schema=HostedShellShortTermMemorySchema,
        short_term_memory_name=_SHORT_TERM_MEMORY_NAME,
    )
    return short_term_memory_manager


async def _create_container_if_not_exists(
    client: AsyncOpenAI,
    chat_id: str,
    user_id: str,
    company_id: str,
    expires_after_minutes: int,
    memory: HostedShellShortTermMemorySchema | None = None,
) -> HostedShellShortTermMemorySchema:
    """Ensure a persistent container exists, creating one if needed.

    If the container referenced in *memory* no longer exists or is inactive,
    a fresh container is created and the memory schema is reset.
    """
    if memory is not None:
        logger.info("Container found in short term memory")
    else:
        logger.info("No Container in short term memory, creating a new container")
        memory = HostedShellShortTermMemorySchema()

    container_id = memory.container_id

    if container_id is not None:
        try:
            container = await client.containers.retrieve(container_id)
            if container.status not in ["active", "running"]:
                logger.info(
                    "Container has status `%s`, recreating a new one", container.status
                )
                container_id = None
        except NotFoundError:
            container_id = None

    if container_id is None:
        memory = HostedShellShortTermMemorySchema()

        container = await client.containers.create(
            name=f"hosted_shell_{company_id}_{user_id}_{chat_id}",
            expires_after={
                "anchor": "last_active_at",
                "minutes": expires_after_minutes,
            },
        )

        memory.container_id = container.id

    return memory


async def _upload_files_to_container(
    client: AsyncOpenAI,
    uploaded_files: list[Content],
    memory: HostedShellShortTermMemorySchema,
    content_service: ContentService,
    chat_id: str,
) -> HostedShellShortTermMemorySchema:
    """Upload chat files directly into a persistent container.

    Files already present (by Unique content ID) are skipped.
    """
    container_id = memory.container_id

    assert container_id is not None

    memory = memory.model_copy(deep=True)

    for file in uploaded_files:
        upload = True
        if file.id in memory.file_ids:
            try:
                _ = await client.containers.files.retrieve(
                    container_id=container_id, file_id=memory.file_ids[file.id]
                )
                logger.info("File with id %s already uploaded to container", file.id)
                upload = False
            except NotFoundError:
                upload = True

        if upload:
            logger.info(
                "Uploading file %s to container %s", file.id, memory.container_id
            )
            file_content = content_service.download_content_to_bytes(
                content_id=file.id, chat_id=chat_id
            )  # TODO: Use async version when available

            openai_file = await client.containers.files.create(
                container_id=container_id,
                file=(file.key, file_content),
            )
            memory.file_ids[file.id] = openai_file.id

    return memory


async def _upload_files_for_auto_container(
    client: AsyncOpenAI,
    uploaded_files: list[Content],
    memory: HostedShellShortTermMemorySchema,
    content_service: ContentService,
    chat_id: str,
) -> HostedShellShortTermMemorySchema:
    """Upload files via client.files.create for use with container_auto's file_ids."""
    memory = memory.model_copy(deep=True)

    for file in uploaded_files:
        if file.id in memory.file_ids:
            logger.info("File with id %s already uploaded (cached)", file.id)
            continue

        logger.info("Uploading file %s via files API for auto container", file.id)
        file_content = content_service.download_content_to_bytes(
            content_id=file.id, chat_id=chat_id
        )  # TODO: Use async version when available

        openai_file = await client.files.create(
            file=(file.key, file_content),
            purpose="assistants",
        )
        memory.file_ids[file.id] = openai_file.id

    return memory


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
        if config.use_auto_container:
            logger.info("Using `container_auto` environment setting for hosted shell")

            file_ids: list[str] = []
            if config.upload_files_in_chat_to_container and uploaded_files:
                memory_manager = _get_hosted_shell_short_term_memory_manager(
                    company_id=company_id,
                    user_id=user_id,
                    chat_id=chat_id,
                )
                memory = await memory_manager.load_async()
                if memory is None:
                    memory = HostedShellShortTermMemorySchema()

                memory = await _upload_files_for_auto_container(
                    client=client,
                    uploaded_files=uploaded_files,
                    memory=memory,
                    content_service=content_service,
                    chat_id=chat_id,
                )

                await memory_manager.save_async(memory)
                file_ids = list(memory.file_ids.values())

            return cls(
                config=config,
                container_id=None,
                is_exclusive=is_exclusive,
                file_ids=file_ids,
            )

        memory_manager = _get_hosted_shell_short_term_memory_manager(
            company_id=company_id,
            user_id=user_id,
            chat_id=chat_id,
        )

        memory = await memory_manager.load_async()

        memory = await _create_container_if_not_exists(
            client=client,
            memory=memory,
            chat_id=chat_id,
            user_id=user_id,
            company_id=company_id,
            expires_after_minutes=config.expires_after_minutes,
        )

        if config.upload_files_in_chat_to_container:
            memory = await _upload_files_to_container(
                client=client,
                uploaded_files=uploaded_files,
                content_service=content_service,
                chat_id=chat_id,
                memory=memory,
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
