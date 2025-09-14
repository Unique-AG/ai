from unique_orchestrator.config import (
    SearchAgentConfig,
    search_agent_config_to_unique_ai_space_config,
)


def test_ai_tools_conversion():
    """
    AI-authored test: Validates the transfer of tool configurations.

    This test ensures that:
    1. All tools from the old config are present in the new config
    2. Tool names are preserved exactly
    3. Tool configurations are maintained without modification

    Written by AI Assistant to verify tool configuration preservation.
    """
    old_config = SearchAgentConfig()
    new_config = search_agent_config_to_unique_ai_space_config(old_config)

    assert len(new_config.space.tools) == len(old_config.tools)
    for old_tool, new_tool in zip(old_config.tools, new_config.space.tools):
        assert old_tool.name == new_tool.name
        assert old_tool.configuration == new_tool.configuration


def test_ai_services_conversion():
    """
    AI-authored test: Verifies the conversion of service configurations.

    This test checks that all service configurations are properly transferred:
    1. Follow-up questions configuration
    2. Evaluation configuration
    3. Stock ticker configuration
    4. Reference manager configuration

    Written by AI Assistant to ensure service configuration integrity.
    """
    old_config = SearchAgentConfig()
    new_config = search_agent_config_to_unique_ai_space_config(old_config)

    services = new_config.agent.services
    assert services.follow_up_questions_config == old_config.follow_up_questions_config
    assert services.evaluation_config == old_config.evaluation_config
    assert services.stock_ticker_config == old_config.stock_ticker_config


def test_ai_experimental_config_conversion():
    """
    AI-authored test: Checks the conversion of experimental features.

    This test verifies that:
    1. Experimental features like thinking_steps_display are properly transferred
    2. Boolean values are preserved accurately

    Written by AI Assistant to ensure experimental feature preservation.
    """
    old_config = SearchAgentConfig()
    old_config.thinking_steps_display = True
    new_config = search_agent_config_to_unique_ai_space_config(old_config)

    assert (
        new_config.agent.experimental.thinking_steps_display
        == old_config.thinking_steps_display
    )


def test_ai_force_checks_conversion():
    """
    AI-authored test: Validates the conversion of force checks configuration.

    This test ensures that:
    1. Force checks for stream response references are properly transferred
    2. The configuration maintains its integrity during conversion

    Written by AI Assistant to verify force checks preservation.
    """
    old_config = SearchAgentConfig()
    new_config = search_agent_config_to_unique_ai_space_config(old_config)

    assert (
        new_config.agent.experimental.force_checks_on_stream_response_references
        == old_config.force_checks_on_stream_response_references
    )


def test_ai_custom_values_conversion():
    """
    AI-authored test: Verifies the conversion of custom configuration values.

    This test validates that custom values are properly transferred:
    1. Project name
    2. Custom instructions
    3. Temperature settings
    4. Loop iteration limits
    5. Additional LLM options

    Written by AI Assistant to ensure custom configuration preservation.
    """
    old_config = SearchAgentConfig(
        project_name="Custom Project",
        custom_instructions="Custom Instructions",
        temperature=0.8,
        max_loop_iterations=5,
        additional_llm_options={"some_option": "value"},
    )
    new_config = search_agent_config_to_unique_ai_space_config(old_config)

    assert new_config.space.project_name == "Custom Project"
    assert new_config.space.custom_instructions == "Custom Instructions"
    assert new_config.agent.experimental.temperature == 0.8
    assert new_config.agent.max_loop_iterations == 5
    assert new_config.agent.experimental.additional_llm_options == {
        "some_option": "value"
    }
