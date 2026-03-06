from core.vertexai.config import (
    get_vertex_grounding_config,
    get_vertex_structured_results_config,
)
from core.vertexai.prompts import (
    VERTEX_GROUNDING_SYSTEM_INSTRUCTION,
    VERTEX_STRUCTURED_RESULTS_SYSTEM_INSTRUCTION,
)


class TestGetVertexGroundingConfig:
    def test_default_system_instruction(self):
        config = get_vertex_grounding_config(system_instruction=None)
        assert config.system_instruction == VERTEX_GROUNDING_SYSTEM_INSTRUCTION
        assert config.tools is not None
        assert len(config.tools) == 1

    def test_custom_system_instruction(self):
        config = get_vertex_grounding_config(system_instruction="custom prompt")
        assert config.system_instruction == "custom prompt"

    def test_google_search_tool(self):
        config = get_vertex_grounding_config(
            system_instruction=None, entreprise_search=False
        )
        tool = config.tools[0]
        assert tool.google_search is not None

    def test_enterprise_search_tool(self):
        config = get_vertex_grounding_config(
            system_instruction=None, entreprise_search=True
        )
        tool = config.tools[0]
        assert tool.enterprise_web_search is not None


class TestGetVertexStructuredResultsConfig:
    def test_default_system_instruction(self):
        from pydantic import BaseModel

        class Dummy(BaseModel):
            x: int

        config = get_vertex_structured_results_config(
            system_instruction=None, response_schema=Dummy
        )
        assert config.system_instruction == VERTEX_STRUCTURED_RESULTS_SYSTEM_INSTRUCTION
        assert config.response_mime_type == "application/json"
        assert config.response_schema is Dummy

    def test_custom_system_instruction(self):
        from pydantic import BaseModel

        class Dummy(BaseModel):
            x: int

        config = get_vertex_structured_results_config(
            system_instruction="custom", response_schema=Dummy
        )
        assert config.system_instruction == "custom"
