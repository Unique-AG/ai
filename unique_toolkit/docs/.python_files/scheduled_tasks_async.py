# ~/~ begin <<docs/modules/examples/scheduled_task/scheduled_tasks.md#./docs/.python_files/scheduled_tasks_async.py>>[init]
import asyncio

# ~/~ begin <<docs/setup/_common_imports.md#common_imports>>[init]
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.app.init_sdk import init_unique_sdk
from unique_toolkit.app.dev_util import get_event_generator
from unique_toolkit.app.schemas import ChatEvent 
from unique_toolkit import ChatService, ContentService, EmbeddingService, LanguageModelService, LanguageModelName, KnowledgeBaseService
from unique_toolkit.chat.schemas import ChatMessageAssessmentStatus, ChatMessageAssessmentType, ChatMessageAssessmentLabel
import os
import io
import tempfile
import requests
import mimetypes
from pathlib import Path
from unique_toolkit.content.schemas import ContentSearchType, ContentRerankerConfig, ContentChunk, ContentReference
import unique_sdk
from pydantic import BaseModel, Field
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from openai.types.shared_params.function_definition import FunctionDefinition
from unique_toolkit.app.unique_settings import UniqueSettings
from unique_toolkit.framework_utilities.openai.client import get_openai_client
from unique_toolkit.framework_utilities.openai.message_builder import (
    OpenAIMessageBuilder,
    OpenAIUserMessageBuilder
)
from pydantic import Field
from unique_toolkit import LanguageModelToolDescription
from unique_toolkit.chat.rendering import create_prompt_button_string, create_latex_formula_string
# ~/~ end
# ~/~ begin <<docs/modules/examples/scheduled_task/scheduled_tasks.md#scheduled_tasks_imports>>[init]
from unique_toolkit.experimental.scheduled_task import (
    Cron,
    ScheduledTasks,
)
# ~/~ end
# ~/~ begin <<docs/modules/examples/scheduled_task/scheduled_tasks.md#scheduled_tasks_setup_from_settings>>[init]
scheduled_tasks = ScheduledTasks.from_settings()
# ~/~ end


async def main() -> None:
    # ~/~ begin <<docs/modules/examples/scheduled_task/scheduled_tasks.md#scheduled_tasks_async>>[init]
    task = await scheduled_tasks.create_task_async(
        cron_expression=Cron.HOURLY,
        assistant_id="assistant_hourly_digest",
        prompt="Write a one-paragraph digest of the past hour.",
    )
    
    tasks = await scheduled_tasks.list_tasks_async()
    await scheduled_tasks.delete_task_async(task_id=task.id)
    # ~/~ end


asyncio.run(main())
# ~/~ end
