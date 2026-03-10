"""
Test suite for ClaudeAgentConfig and build_tool_policy.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unique_toolkit.agentic.claude_agent.config import (
    BASE_ALLOWED_TOOLS,
    BASE_DISALLOWED_TOOLS,
    ClaudeAgentConfig,
    build_tool_policy,
)


class TestClaudeAgentConfigDefaults:
    def test_default_config_values__all_match_spec__when_constructed_with_no_args(
        self,
    ) -> None:
        """Test that all defaults match the spec."""
        config = ClaudeAgentConfig()

        assert config.model == "claude-sonnet-4-20250514"
        assert config.fallback_model is None
        assert config.max_thinking_tokens is None
        assert config.max_turns == 20
        assert config.max_budget_usd == 2.0
        assert config.permission_mode == "bypassPermissions"
        assert config.search_type == "COMBINED"
        assert config.scope_ids == []
        assert config.history_included is True
        assert config.max_history_interactions == 4
        assert config.enable_code_execution is False
        assert config.setting_sources is None
        assert config.add_dirs == []
        assert config.enable_workspace_persistence is True
        assert config.system_prompt_override == ""
        assert config.custom_instructions is None
        assert config.user_instructions is None
        assert config.agents is None
        assert config.enable_hooks is False
        assert config.session_id is None
        assert config.continue_conversation is False
        assert config.cli_path is None
        assert config.stderr_logging is True
        assert config.enable_file_checkpointing is False
        assert config.extra_env == {}

    def test_optional_fields_default_to_none__fallback_model_agents_session_id_cli_path(
        self,
    ) -> None:
        """Test that optional forward-compatibility fields default to None."""
        config = ClaudeAgentConfig()

        assert config.fallback_model is None
        assert config.agents is None
        assert config.session_id is None
        assert config.cli_path is None
        assert config.max_thinking_tokens is None


class TestClaudeAgentConfigValidation:
    def test_max_turns_validation__raises_validation_error__when_below_minimum(
        self,
    ) -> None:
        """Test that max_turns values below 1 are rejected by Pydantic."""
        with pytest.raises(ValidationError):
            ClaudeAgentConfig(max_turns=0)

    def test_max_turns_validation__raises_validation_error__when_above_maximum(
        self,
    ) -> None:
        """Test that max_turns values above 50 are rejected by Pydantic."""
        with pytest.raises(ValidationError):
            ClaudeAgentConfig(max_turns=51)

    def test_max_budget_validation__raises_validation_error__when_below_minimum(
        self,
    ) -> None:
        """Test that max_budget_usd values below 0.1 are rejected by Pydantic."""
        with pytest.raises(ValidationError):
            ClaudeAgentConfig(max_budget_usd=0.05)

    def test_max_budget_validation__raises_validation_error__when_above_maximum(
        self,
    ) -> None:
        """Test that max_budget_usd values above 10.0 are rejected by Pydantic."""
        with pytest.raises(ValidationError):
            ClaudeAgentConfig(max_budget_usd=10.1)

    def test_permission_mode_validation__accepts_all_three_literal_values(
        self,
    ) -> None:
        """Test that all three valid permission_mode literals are accepted."""
        for mode in ("default", "acceptEdits", "bypassPermissions"):
            config = ClaudeAgentConfig(permission_mode=mode)  # type: ignore[arg-type]
            assert config.permission_mode == mode

    def test_permission_mode_validation__raises_validation_error__when_invalid_value(
        self,
    ) -> None:
        """Test that only the three literal values are accepted."""
        with pytest.raises(ValidationError):
            ClaudeAgentConfig(permission_mode="unsafe")  # type: ignore[arg-type]


class TestBuildToolPolicyCodeExecution:
    def test_tool_policy_code_execution_disabled__bash_write_edit_in_disallowed(
        self,
    ) -> None:
        """Test that Bash/Write/Edit are in disallowed when code execution is off."""
        config = ClaudeAgentConfig(enable_code_execution=False)
        allowed, disallowed = build_tool_policy(config)

        assert "Bash" in disallowed
        assert "Write" in disallowed
        assert "Edit" in disallowed
        assert "MultiEdit" in disallowed
        assert "Bash" not in allowed
        assert "Write" not in allowed
        assert "Edit" not in allowed

    def test_tool_policy_code_execution_enabled__bash_write_edit_read_glob_grep_in_allowed_not_in_disallowed(
        self,
    ) -> None:
        """Test that Bash/Write/Edit/Read/Glob/Grep are in allowed and not in disallowed when on."""
        config = ClaudeAgentConfig(enable_code_execution=True)
        allowed, disallowed = build_tool_policy(config)

        for tool in ("Bash", "Write", "Edit", "Read", "Glob", "Grep"):
            assert tool in allowed, f"{tool} should be in allowed"
            assert tool not in disallowed, f"{tool} should not be in disallowed"


class TestBuildToolPolicySkills:
    def test_tool_policy_skills_enabled_when_setting_sources_set__skill_in_allowed(
        self,
    ) -> None:
        """Test that Skill is in allowed when setting_sources is set."""
        config = ClaudeAgentConfig(setting_sources=["project"])
        allowed, _ = build_tool_policy(config)

        assert "Skill" in allowed

    def test_tool_policy_skills_not_in_allowed_when_setting_sources_none__skill_absent(
        self,
    ) -> None:
        """Test that Skill is NOT in allowed when setting_sources is None."""
        config = ClaudeAgentConfig(setting_sources=None)
        allowed, _ = build_tool_policy(config)

        assert "Skill" not in allowed

    def test_tool_policy_skills_enabled_with_user_and_project_sources__skill_in_allowed(
        self,
    ) -> None:
        """Test that Skill is in allowed for any non-None setting_sources value."""
        config = ClaudeAgentConfig(setting_sources=["user", "project"])
        allowed, _ = build_tool_policy(config)

        assert "Skill" in allowed


class TestBuildToolPolicyConstants:
    def test_tool_policy_always_includes_platform_tools__kb_search_in_allowed(
        self,
    ) -> None:
        """Test that platform tools are always in allowed regardless of other settings."""
        for code_execution in (True, False):
            config = ClaudeAgentConfig(enable_code_execution=code_execution)
            allowed, _ = build_tool_policy(config)

            assert "mcp__unique_platform__search_knowledge_base" in allowed

    def test_tool_policy_always_blocks_builtin_web__web_fetch_web_search_in_disallowed(
        self,
    ) -> None:
        """Test that WebFetch and WebSearch are always in disallowed."""
        for code_execution in (True, False):
            config = ClaudeAgentConfig(enable_code_execution=code_execution)
            _, disallowed = build_tool_policy(config)

            assert "WebFetch" in disallowed
            assert "WebSearch" in disallowed

    def test_tool_policy_always_includes_todo_tools__todo_read_write_in_allowed(
        self,
    ) -> None:
        """Test that TodoRead/TodoWrite are always in allowed."""
        for code_execution in (True, False):
            for setting_sources in (None, ["project"]):
                config = ClaudeAgentConfig(
                    enable_code_execution=code_execution,
                    setting_sources=setting_sources,
                )
                allowed, _ = build_tool_policy(config)

                assert "TodoRead" in allowed, "TodoRead must always be allowed"
                assert "TodoWrite" in allowed, "TodoWrite must always be allowed"

    def test_tool_policy__does_not_mutate_base_constants__after_call(
        self,
    ) -> None:
        """Test that build_tool_policy does not mutate BASE_ALLOWED_TOOLS or BASE_DISALLOWED_TOOLS."""
        original_allowed = list(BASE_ALLOWED_TOOLS)
        original_disallowed = list(BASE_DISALLOWED_TOOLS)

        build_tool_policy(
            ClaudeAgentConfig(enable_code_execution=True, setting_sources=["project"])
        )

        assert BASE_ALLOWED_TOOLS == original_allowed
        assert BASE_DISALLOWED_TOOLS == original_disallowed
