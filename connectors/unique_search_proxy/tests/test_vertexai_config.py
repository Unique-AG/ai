import pytest
from core.vertexai.config import (
    get_vertex_grounding_config,
    get_vertex_structured_results_config,
)
from core.vertexai.prompts import (
    VERTEX_GROUNDING_SYSTEM_INSTRUCTION,
    VERTEX_STRUCTURED_RESULTS_SYSTEM_INSTRUCTION,
)


class TestGetVertexGroundingConfig:
    @pytest.mark.ai
    def test_default_system_instruction(self):
        """
        Purpose: Verify default system instruction is the grounding prompt constant.
        Why this matters: The default prompt controls grounded-search quality.
        Setup summary: Call with system_instruction=None and assert the default is used.
        """
        config = get_vertex_grounding_config(system_instruction=None)
        assert config.system_instruction == VERTEX_GROUNDING_SYSTEM_INSTRUCTION
        assert config.tools is not None
        assert len(config.tools) == 1

    @pytest.mark.ai
    def test_custom_system_instruction(self):
        """
        Purpose: Verify a custom system instruction overrides the default.
        Why this matters: Per-request prompt customisation is used for specialised searches.
        Setup summary: Pass a custom string and assert it is stored in config.
        """
        config = get_vertex_grounding_config(system_instruction="custom prompt")
        assert config.system_instruction == "custom prompt"

    @pytest.mark.ai
    def test_google_search_tool(self):
        """
        Purpose: Verify standard Google Search tool is attached when enterprise is off.
        Why this matters: Tool selection determines the search provider used by Vertex AI.
        Setup summary: Call with entreprise_search=False and assert google_search is set.
        """
        config = get_vertex_grounding_config(
            system_instruction=None, entreprise_search=False
        )
        tool = config.tools[0]
        assert tool.google_search is not None

    @pytest.mark.ai
    def test_enterprise_search_tool(self):
        """
        Purpose: Verify enterprise web search tool is attached when enterprise is on.
        Why this matters: Enterprise search uses a different data source.
        Setup summary: Call with entreprise_search=True and assert enterprise_web_search is set.
        """
        config = get_vertex_grounding_config(
            system_instruction=None, entreprise_search=True
        )
        tool = config.tools[0]
        assert tool.enterprise_web_search is not None


class TestGetVertexStructuredResultsConfig:
    @pytest.mark.ai
    def test_default_system_instruction(self):
        """
        Purpose: Verify default system instruction is the structured-results prompt constant.
        Why this matters: The default prompt controls structured output quality.
        Setup summary: Call with system_instruction=None and assert the default and JSON mime type.
        """
        from pydantic import BaseModel

        class Dummy(BaseModel):
            x: int

        config = get_vertex_structured_results_config(
            system_instruction=None, response_schema=Dummy
        )
        assert config.system_instruction == VERTEX_STRUCTURED_RESULTS_SYSTEM_INSTRUCTION
        assert config.response_mime_type == "application/json"
        assert config.response_schema is Dummy

    @pytest.mark.ai
    def test_custom_system_instruction(self):
        """
        Purpose: Verify a custom system instruction overrides the default.
        Why this matters: Per-request prompt customisation is used for specialised outputs.
        Setup summary: Pass a custom string and assert it is stored in config.
        """
        from pydantic import BaseModel

        class Dummy(BaseModel):
            x: int

        config = get_vertex_structured_results_config(
            system_instruction="custom", response_schema=Dummy
        )
        assert config.system_instruction == "custom"
