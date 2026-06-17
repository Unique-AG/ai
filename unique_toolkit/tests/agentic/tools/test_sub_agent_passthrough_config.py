"""
Unit tests for the passthrough_config validators added to SubAgentToolConfig
and ExtendedSubAgentToolConfig.
"""

import logging

import pytest

from unique_toolkit.agentic.tools.a2a.config import ExtendedSubAgentToolConfig
from unique_toolkit.agentic.tools.a2a.postprocessing import (
    SubAgentDisplayConfig,
    SubAgentResponseDisplayMode,
)
from unique_toolkit.agentic.tools.a2a.tool.config import (
    SubAgentPassthroughConfig,
    SubAgentToolConfig,
)


@pytest.mark.ai
def test_sub_agent_tool_config__raises__when_passthrough_enabled_with_returns_content_chunks() -> (
    None
):
    """
    Purpose: Verify our validator rejects passthrough + returns_content_chunks together.
    Why this matters: The two modes are conceptually incompatible — passthrough writes a final
        assistant message, while returns_content_chunks expects the orchestrator to keep using
        the sub-agent output as structured tool data. Allowing both would yield garbage output.
    Setup summary: Construct config with both flags on, assert our validator raises ValueError
        with the message we authored.
    """
    # Arrange / Act / Assert
    with pytest.raises(ValueError, match="mutually exclusive"):
        SubAgentToolConfig(
            passthrough_config=SubAgentPassthroughConfig(enabled=True),
            returns_content_chunks=True,
        )


@pytest.mark.ai
def test_sub_agent_tool_config__overrides_use_sub_agent_references__when_passthrough_enabled(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Purpose: Verify our validator force-disables use_sub_agent_references when passthrough is on.
    Why this matters: Passthrough streams the sub-agent message verbatim, so the
        sub-agent reference rewriting pass would corrupt the output if left on.
        We deliberately mutate the field and warn rather than raising so existing configs keep
        working without changes.
    Setup summary: Set both passthrough.enabled=True and use_sub_agent_references=True,
        assert references flag is flipped to False and our warning is logged.
    """
    # Arrange / Act
    with caplog.at_level(
        logging.WARNING, logger="unique_toolkit.agentic.tools.a2a.tool.config"
    ):
        cfg = SubAgentToolConfig(
            passthrough_config=SubAgentPassthroughConfig(enabled=True),
            use_sub_agent_references=True,
        )

    # Assert
    assert cfg.use_sub_agent_references is False
    assert any("use_sub_agent_references" in r.message for r in caplog.records)


@pytest.mark.ai
def test_extended_config__forces_display_mode_hidden__when_passthrough_enabled(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Purpose: Verify our validator overrides response_display_config.mode to HIDDEN when
        passthrough is on.
    Why this matters: Passthrough writes the sub-agent answer directly into the assistant
        message; if the post-processing display layer were also active, the answer would
        get rendered twice (once by passthrough, once by display).
    Setup summary: Construct ExtendedSubAgentToolConfig with passthrough enabled and a
        non-hidden display mode; assert our validator flips display mode to HIDDEN and warns.
    """
    # Arrange / Act
    with caplog.at_level(
        logging.WARNING, logger="unique_toolkit.agentic.tools.a2a.config"
    ):
        cfg = ExtendedSubAgentToolConfig(
            passthrough_config=SubAgentPassthroughConfig(enabled=True),
            response_display_config=SubAgentDisplayConfig(
                mode=SubAgentResponseDisplayMode.PLAIN,
            ),
        )

    # Assert
    assert cfg.response_display_config.mode == SubAgentResponseDisplayMode.HIDDEN
    assert any("response_display_config.mode" in r.message for r in caplog.records)


@pytest.mark.ai
def test_extended_config__keeps_display_mode__when_passthrough_disabled() -> None:
    """
    Purpose: Verify our validator does NOT touch response_display_config.mode when passthrough
        is off.
    Why this matters: The HIDDEN-override is scoped to the passthrough case; outside it,
        the operator-chosen display mode must survive — testing the negative branch protects
        against an accidental inversion of the validator's guard.
    Setup summary: Construct config with passthrough disabled and an explicit display mode;
        assert the mode is preserved.
    """
    # Arrange / Act
    cfg = ExtendedSubAgentToolConfig(
        passthrough_config=SubAgentPassthroughConfig(enabled=False),
        response_display_config=SubAgentDisplayConfig(
            mode=SubAgentResponseDisplayMode.DETAILS_OPEN,
        ),
    )

    # Assert
    assert cfg.response_display_config.mode == SubAgentResponseDisplayMode.DETAILS_OPEN
