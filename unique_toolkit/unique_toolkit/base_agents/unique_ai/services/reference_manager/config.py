from pydantic import BaseModel, Field

from unique_toolkit.unique_toolkit.tools.config import get_configuration_dict




class ReferenceManagerConfig(BaseModel):
    """Configuration settings for the ReferenceManagerService.

    Attributes:
        max_reference_age: Maximum number of interactions before a reference is removed
        replace_old_references: String to replace old references with, or None to remove them
        include_images: Whether to include images in messages
        file_content_serialization_type: How to serialize file content
    """

    model_config = get_configuration_dict()
    tool_names_to_include: list[str] = Field(
        default=["WebSearchTool", "InternalSearchTool"],
        description="List of tool names to be parsed by reference manager",
    )
    system_message_tool_selection_citation_appendix_reference_manager: str = Field(
        default=(
            "IT IS VERY IMPORTANT TO FOLLOW THESE GUIDELINES!!\n"
            "NEVER CITE A source_number THAT YOU DON'T SEE IN THE TOOL CALL RESPONSE!!!\n"
            "The source_number in old assistant messages are no longer valid.\n"
            "EXAMPLE: If you see [source34] and [source35] in the assistant message, you can't use [source34] again in the next assistant message, this has to be the number you find in the message with role 'tool'. \n"
            "BE AWARE:All tool calls have been filtered to remove uncited sources. Tool calls return much more data than you see"
        ),
        description="System message to be added to the tool selection citation appendix",
    )
