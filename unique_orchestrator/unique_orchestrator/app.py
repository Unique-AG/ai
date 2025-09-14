import asyncio
import logging
import traceback
from pathlib import Path
from typing import Any

from unique_toolkit.app.schemas import ChatEvent
from unique_toolkit.chat import ChatService
from unique_toolkit.debug_info_manager.debug_info_manager import (
    DebugInfoManager,
)
from unique_toolkit.language_model import (
    LanguageModelTool,
    LanguageModelToolParameters,
)

from _common.utils.config import config_loader
from core.module_template.module import ModuleTemplate
from unique_ai_v2.config import (
    SearchAgentConfig,
    UniqueAIConfig,
    needs_conversion_to_unique_ai_space_config,
    search_agent_config_to_unique_ai_space_config,
)
from unique_ai_v2.unique_ai_builder import build_unique_ai

MODULE_NAME = "UniqueAIV2"


logger = logging.getLogger(f"{MODULE_NAME}.{__name__}")


class UniqueAIApp(ModuleTemplate):
    def __init__(self):
        folder_name = Path(__file__).parent.name
        self.module_name = "UniqueAIV2"  # humps.pascalize(folder_name)

        super().__init__(
            self.module_name, folder_name, event_constructor=ChatEvent
        )

    async def run(self, event: ChatEvent):
        logger.info(f"Running {self.module_name}")

        try:
            debug_info_manager = DebugInfoManager()
            # Filter out MCP tools from configuration before processing
            filtered_configuration = self._filter_mcp_tools_from_configuration(
                event.payload.configuration
            )

            # TODO: @cdkl Remove this once the configuration is converted to the new UniqueAISpaceConfig
            # and the old configuration is no longer supported
            if needs_conversion_to_unique_ai_space_config(
                filtered_configuration
            ):
                config, was_valid, message = config_loader(
                    filtered_configuration,
                    SearchAgentConfig,
                )
                config = search_agent_config_to_unique_ai_space_config(config)
            else:
                config, was_valid, message = config_loader(
                    filtered_configuration,
                    UniqueAIConfig,
                )

            # Inform user that the configuration passed is invalid
            if not was_valid:
                debug_info_manager.add("config_error", message)
                chat_service = ChatService(event)
                await chat_service.modify_assistant_message_async(
                    content=f"⚠️ Initialization of configuration failed. Please report to admin for {self.module_name}",
                )
                await asyncio.sleep(2)
                raise Exception("Invalid configuration")

            agent = build_unique_ai(
                event=event,
                logger=logger,
                config=config,
                debug_info_manager=debug_info_manager,
            )
            await agent.run()
            return "OK", 200
        except Exception as e:
            chat_service = ChatService(event)
            debug_info_manager.add("error", traceback.format_exc())
            await chat_service.update_debug_info_async(
                debug_info_manager.get()
            )
            await chat_service.create_assistant_message_async(
                content=f"❌ An unexpected error occurred while running {self.module_name} 🚨",
                set_completed_at=True,
            )
            logger.error(
                f"Error in {self.module_name}: {traceback.format_exc()}"
            )
            return str(e), 500

    def _filter_mcp_tools_from_configuration(
        self, configuration: dict
    ) -> dict:
        """Filter out tools with configuration.mcpTool === true or mcp_source_id field from the configuration."""
        if not isinstance(configuration, dict):
            return configuration

        filtered_config = configuration.copy()

        def filter_tools_list(tools_list):
            """Filter out MCP tools from a list of tools."""
            if not isinstance(tools_list, list):
                return tools_list

            filtered_tools = []
            for tool in tools_list:
                if isinstance(tool, dict):
                    # Skip tools with mcpTool === true in configuration
                    if (
                        isinstance(tool.get("configuration"), dict)
                        and tool["configuration"].get("mcpTool") is True
                    ):
                        logger.info(
                            f"Filtering out MCP tool (mcpTool=true): {tool.get('name', 'unknown')}"
                        )
                        continue
                    # Skip tools with mcp_source_id field (MCP tools)
                    if "mcp_source_id" in tool:
                        logger.info(
                            f"Filtering out MCP tool (has mcp_source_id): {tool.get('name', 'unknown')}"
                        )
                        continue
                filtered_tools.append(tool)
            return filtered_tools

        if "tools" in filtered_config:
            filtered_config["tools"] = filter_tools_list(
                filtered_config["tools"]
            )

        if "space" in filtered_config and isinstance(
            filtered_config["space"], dict
        ):
            filtered_config["space"] = filtered_config["space"].copy()
            if "tools" in filtered_config["space"]:
                filtered_config["space"]["tools"] = filter_tools_list(
                    filtered_config["space"]["tools"]
                )

        return filtered_config

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


blueprint = UniqueAIApp().blueprint
