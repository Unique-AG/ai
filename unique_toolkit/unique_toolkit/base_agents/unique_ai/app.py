import asyncio
import logging
import traceback
from pathlib import Path
from typing import Any

import humps
from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat import ChatService
from unique_toolkit.language_model import (
    LanguageModelTool,
    LanguageModelToolParameters,
)

from _common.agents.loop_agent.schemas import (
    AgentChunksHandler,
    AgentDebugInfo,
)
from _common.utils.config import config_loader
from core.module_template.module import ModuleTemplate
from unique_ai.config import (
    SearchAgentConfig,
    UniqueAIConfig,
    needs_conversion_to_unique_ai_space_config,
    search_agent_config_to_unique_ai_space_config,
)
from unique_ai.search_agent import SearchAgent
from unique_ai.services.reference_manager.reference_manager_service import (
    ReferenceManagerService,
)

MODULE_NAME = "AgenticSearchV2"

logger = logging.getLogger(f"{MODULE_NAME}.{__name__}")


class AgenticSearch(ModuleTemplate):
    def __init__(self):
        folder_name = Path(__file__).parent.name
        self.module_name = humps.pascalize(folder_name)
        super().__init__(
            self.module_name, folder_name, event_constructor=ChatEvent
        )

    async def run(self, event: ChatEvent):
        agent_debug_info = AgentDebugInfo()
        agent_debug_info.add("module_name", self.module_name)
        agent_chunks_handler = AgentChunksHandler()
        try:
            # TODO: @cdkl Remove this once the configuration is converted to the new UniqueAISpaceConfig
            # and the old configuration is no longer supported
            if needs_conversion_to_unique_ai_space_config(
                event.payload.configuration
            ):
                config, was_valid, message = config_loader(
                    event.payload.configuration,
                    SearchAgentConfig,
                )
                config = search_agent_config_to_unique_ai_space_config(config)
            else:
                config = event.payload.configuration

                config, was_valid, message = config_loader(
                    event.payload.configuration,
                    UniqueAIConfig,
                )

            # Inform user that the configuration passed is invalid
            if not was_valid:
                agent_debug_info.add("config_error", message)
                chat_service = ChatService(event)
                await chat_service.modify_assistant_message_async(
                    content=f"⚠️ Initialization of configuration failed. Please report to admin for {self.module_name}",
                )
                await asyncio.sleep(2)
                raise Exception("Invalid configuration")

            # Initialize services
            if config.agent.services.reference_manager_config:
                chat_service = ChatService(event)
                reference_manager_service = ReferenceManagerService(
                    chat_service=chat_service,
                    chat_id=event.payload.chat_id,
                    config=config.agent.services.reference_manager_config,
                    chat_user_message=event.payload.user_message,
                )
            else:
                reference_manager_service = None

            agent = SearchAgent(
                event=event,
                config=config,
                agent_debug_info=agent_debug_info,
                agent_chunks_handler=agent_chunks_handler,
                reference_manager_service=reference_manager_service,
            )
            await agent.run()
            return "OK", 200
        except Exception as e:
            chat_service = ChatService(event)
            agent_debug_info.add("error", traceback.format_exc())
            await chat_service.update_debug_info_async(agent_debug_info.get())
            await chat_service.create_assistant_message_async(
                content=f"❌ An unexpected error occurred while running {self.module_name} 🚨",
                set_completed_at=True,
            )
            logger.error(
                f"Error in {self.module_name}: {traceback.format_exc()}"
            )
            return str(e), 500

    def default_config(self) -> dict[str, Any]:
        return SearchAgentConfig().model_dump()

    def default_tool_definition(self):
        return {
            "type": "function",
            "function": LanguageModelTool(
                name=self.module_name,
                description="Search for information in the knowledge base and on the web",
                parameters=LanguageModelToolParameters(
                    properties={}, required=[]
                ),
                returns=None,
            ).model_dump(exclude_none=True),
        }


blueprint = AgenticSearch().blueprint
