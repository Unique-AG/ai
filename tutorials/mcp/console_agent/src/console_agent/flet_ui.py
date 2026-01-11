"""Flet GUI for the MCP Search Agent.

This module provides a modern graphical interface using Flet,
following the same architecture patterns as the console UI.
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Optional

import flet as ft
from pydantic_ai import Agent, capture_run_messages

from console_agent.token_tracker import ModelInfoExtractor, TokenTracker


@dataclass(frozen=True)
class FletUIConfig:
    """Configuration for Flet UI display settings."""

    window_width: int = 900
    window_height: int = 700
    message_max_width: int = 600
    input_max_lines: int = 5


class MessageBubble(ft.Container):
    """A styled message bubble for chat messages."""

    def __init__(
        self,
        content: str,
        is_user: bool,
        tools_used: Optional[list[str]] = None,
    ) -> None:
        self.is_user = is_user
        avatar_letter = "Y" if is_user else "A"
        avatar_color = ft.Colors.CYAN_700 if is_user else ft.Colors.GREEN_700
        bubble_color = ft.Colors.CYAN_900 if is_user else ft.Colors.GREEN_900

        # Build the message content
        message_content: list[ft.Control] = []

        # Add tools indicator if present
        if tools_used:
            tools_text = ", ".join(tools_used)
            message_content.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.BUILD, size=14, color=ft.Colors.AMBER_400),
                            ft.Text(
                                tools_text,
                                size=11,
                                italic=True,
                                color=ft.Colors.AMBER_400,
                            ),
                        ],
                        spacing=4,
                    ),
                    padding=ft.Padding.only(bottom=6),
                )
            )

        # Add the message text with markdown support for agent responses
        if is_user:
            message_content.append(
                ft.Text(content, selectable=True, color=ft.Colors.WHITE)
            )
        else:
            message_content.append(
                ft.Markdown(
                    content,
                    selectable=True,
                    extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                    code_theme=ft.MarkdownCodeTheme.MONOKAI,
                )
            )

        bubble = ft.Container(
            content=ft.Column(controls=message_content, spacing=0),
            bgcolor=bubble_color,
            border_radius=12,
            padding=ft.Padding.all(12),
            width=550,
        )

        # Create the row with avatar and bubble
        avatar = ft.CircleAvatar(
            content=ft.Text(avatar_letter, weight=ft.FontWeight.BOLD),
            bgcolor=avatar_color,
            radius=18,
        )

        if is_user:
            row_controls = [bubble, avatar]
            alignment = ft.MainAxisAlignment.END
        else:
            row_controls = [avatar, bubble]
            alignment = ft.MainAxisAlignment.START

        super().__init__(
            content=ft.Row(
                controls=row_controls,
                alignment=alignment,
                vertical_alignment=ft.CrossAxisAlignment.START,
                spacing=10,
            ),
            padding=ft.Padding.symmetric(vertical=4, horizontal=8),
        )


class TokenUsageBar(ft.Container):
    """A visual token usage indicator."""

    def __init__(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
        max_tokens: Optional[int] = None,
    ) -> None:
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        self._max_tokens = max_tokens

        self._progress_bar = ft.ProgressBar(
            value=0,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            color=ft.Colors.CYAN_400,
            height=6,
            border_radius=3,
        )

        self._usage_text = ft.Text(
            self._format_usage(),
            size=11,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )

        super().__init__(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.TOKEN, size=14, color=ft.Colors.CYAN_400),
                            self._usage_text,
                        ],
                        spacing=6,
                    ),
                    self._progress_bar,
                ],
                spacing=4,
            ),
            padding=ft.Padding.all(8),
            visible=False,
        )

    def _format_usage(self) -> str:
        total = self._input_tokens + self._output_tokens
        if self._max_tokens:
            percentage = (total / self._max_tokens * 100) if self._max_tokens > 0 else 0
            return f"{total:,} / {self._max_tokens:,} tokens ({percentage:.1f}%)"
        return (
            f"{self._input_tokens:,} in + {self._output_tokens:,} out = {total:,} total"
        )

    def update_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        max_tokens: Optional[int] = None,
    ) -> None:
        """Update the token usage display."""
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        self._max_tokens = max_tokens

        self._usage_text.value = self._format_usage()

        if max_tokens and max_tokens > 0:
            total = input_tokens + output_tokens
            self._progress_bar.value = min(total / max_tokens, 1.0)
            percentage = total / max_tokens * 100

            # Color based on usage level
            if percentage >= 90:
                self._progress_bar.color = ft.Colors.RED_400
            elif percentage >= 75:
                self._progress_bar.color = ft.Colors.AMBER_400
            else:
                self._progress_bar.color = ft.Colors.CYAN_400

        self.visible = True


class FletUI:
    """Flet-based graphical user interface for the MCP Search Agent.

    Provides a modern chat interface with support for markdown rendering,
    token usage tracking, and async agent interactions.
    """

    def __init__(
        self,
        agent: Agent,
        config: Optional[FletUIConfig] = None,
        token_tracker: Optional[TokenTracker] = None,
        debug: bool = False,
    ) -> None:
        """Initialize FletUI.

        Args:
            agent: The pydantic-ai agent
            config: Optional UI configuration
            token_tracker: Optional token tracker
            debug: Whether to show debug information
        """
        self._agent = agent
        self._config = config or FletUIConfig()
        self._token_tracker = token_tracker or TokenTracker()
        self._debug = debug
        self._message_history: Optional[list[Any]] = None

        # UI components (initialized in build())
        self._page: Optional[ft.Page] = None
        self._chat_list: Optional[ft.ListView] = None
        self._input_field: Optional[ft.TextField] = None
        self._send_button: Optional[ft.IconButton] = None
        self._token_bar: Optional[TokenUsageBar] = None
        self._status_container: Optional[ft.Container] = None

    def _build_header(self) -> ft.Container:
        """Build the application header."""
        clear_button = ft.IconButton(
            icon=ft.Icons.REFRESH,
            tooltip="New conversation",
            icon_color=ft.Colors.ON_SURFACE_VARIANT,
        )
        clear_button.on_click = self._on_clear_history  # type: ignore[assignment]

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.SMART_TOY_OUTLINED,
                                size=28,
                                color=ft.Colors.CYAN_400,
                            ),
                            ft.Text(
                                "MCP Search Agent",
                                size=22,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.ON_SURFACE,
                            ),
                        ],
                        spacing=10,
                    ),
                    ft.Row(
                        controls=[clear_button],
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border_radius=ft.BorderRadius.only(top_left=12, top_right=12),
        )

    def _build_chat_area(self) -> ft.Container:
        """Build the chat message display area."""
        chat_list = ft.ListView(
            expand=True,
            spacing=8,
            auto_scroll=True,
            padding=ft.Padding.all(16),
        )
        self._chat_list = chat_list

        # Add welcome message
        welcome_bubble = MessageBubble(
            content=(
                "👋 **Welcome to MCP Search Agent!**\n\n"
                "I can help you search and query your knowledge base. "
                "Ask me anything!\n\n"
                "*Type your question below to get started.*"
            ),
            is_user=False,
        )
        chat_list.controls.append(welcome_bubble)

        return ft.Container(
            content=self._chat_list,
            bgcolor=ft.Colors.SURFACE,
            expand=True,
        )

    def _build_status_indicator(self) -> ft.Container:
        """Build the thinking status indicator."""
        status_ring = ft.ProgressRing(
            width=16,
            height=16,
            stroke_width=2,
            color=ft.Colors.AMBER_400,
        )
        status_text = ft.Text(
            "Thinking...",
            size=12,
            color=ft.Colors.AMBER_400,
            italic=True,
        )

        self._status_container = ft.Container(
            content=ft.Row(
                controls=[status_ring, status_text],
                spacing=8,
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=8),
            visible=False,
        )
        return self._status_container

    def _build_input_area(self) -> ft.Container:
        """Build the message input area."""
        input_field = ft.TextField(
            hint_text="Ask a question...",
            multiline=True,
            min_lines=1,
            max_lines=self._config.input_max_lines,
            expand=True,
            filled=True,
            border_radius=24,
            content_padding=ft.Padding.symmetric(horizontal=16, vertical=12),
            shift_enter=True,
            autofocus=True,
        )
        input_field.on_submit = self._on_send_message  # type: ignore[arg-type]
        self._input_field = input_field

        send_button = ft.IconButton(
            icon=ft.Icons.SEND_ROUNDED,
            icon_color=ft.Colors.CYAN_400,
            icon_size=24,
            tooltip="Send message",
        )
        send_button.on_click = self._on_send_message  # type: ignore[assignment]
        self._send_button = send_button

        return ft.Container(
            content=ft.Row(
                controls=[input_field, send_button],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.END,
            ),
            padding=ft.Padding.all(16),
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border_radius=ft.BorderRadius.only(bottom_left=12, bottom_right=12),
        )

    def _build_token_bar(self) -> TokenUsageBar:
        """Build the token usage bar."""
        self._token_bar = TokenUsageBar()
        return self._token_bar

    async def _on_send_message(self, e: ft.ControlEvent) -> None:
        """Handle send message event."""
        if not self._input_field or not self._page or not self._chat_list:
            return

        question = self._input_field.value
        if not question or not question.strip():
            return

        question = question.strip()

        # Clear input and disable while processing
        self._input_field.value = ""
        self._set_input_enabled(False)
        self._set_thinking_visible(True)
        self._page.update()

        # Add user message bubble
        user_bubble = MessageBubble(content=question, is_user=True)
        self._chat_list.controls.append(user_bubble)
        self._page.update()

        try:
            # Run agent
            result = await self._run_agent(question)

            if result:
                # Extract tool names
                tool_names = self._extract_tool_names(result)

                # Add agent response bubble
                agent_bubble = MessageBubble(
                    content=result.output,
                    is_user=False,
                    tools_used=tool_names if tool_names else None,
                )
                self._chat_list.controls.append(agent_bubble)

                # Update token usage
                if self._token_bar:
                    self._token_bar.update_usage(
                        self._token_tracker.input_tokens,
                        self._token_tracker.output_tokens,
                        self._token_tracker.max_tokens,
                    )

        except Exception as ex:
            # Add error message
            error_bubble = MessageBubble(
                content=f"❌ **Error:** {str(ex)}",
                is_user=False,
            )
            self._chat_list.controls.append(error_bubble)

        finally:
            self._set_thinking_visible(False)
            self._set_input_enabled(True)
            # Ensure input field is ready for new input
            if self._input_field:
                self._input_field.value = ""
            self._page.update()
            # Re-focus input field after UI is updated
            if self._input_field and self._page:
                await self._input_field.focus()
                self._page.update()

    async def _run_agent(self, question: str) -> Optional[Any]:
        """Run the agent with error handling.

        Args:
            question: The user's question

        Returns:
            Agent result or None if error occurred
        """
        try:
            with capture_run_messages():
                result = await self._agent.run(
                    question,
                    message_history=self._message_history,
                )

                # Update state
                self._message_history = result.new_messages()
                self._token_tracker.add_from_result(result)

                return result

        except Exception as ex:
            if self._debug:
                print(f"Agent error: {ex}")
            raise

    def _extract_tool_names(self, result: Any) -> list[str]:
        """Extract tool names from agent result messages."""
        tool_names: list[str] = []
        seen: set[str] = set()

        for msg in result.all_messages():
            if not hasattr(msg, "parts"):
                continue

            for part in msg.parts:
                part_type = type(part).__name__
                if part_type == "ToolCallPart":
                    tool_name = getattr(part, "tool_name", None)
                    if tool_name and tool_name not in seen:
                        tool_names.append(tool_name)
                        seen.add(tool_name)

        return tool_names

    async def _on_clear_history(self, e: ft.ControlEvent) -> None:
        """Handle clear history event."""
        if not self._page or not self._chat_list:
            return

        self._message_history = None
        self._token_tracker.reset()

        # Clear chat and add welcome back
        self._chat_list.controls.clear()
        welcome_bubble = MessageBubble(
            content=(
                "🔄 **Conversation cleared!**\n\n"
                "Ready for a fresh start. Ask me anything!"
            ),
            is_user=False,
        )
        self._chat_list.controls.append(welcome_bubble)

        # Reset token bar
        if self._token_bar:
            self._token_bar.visible = False

        self._page.update()

    def _set_input_enabled(self, enabled: bool) -> None:
        """Enable or disable input controls."""
        if self._input_field:
            self._input_field.disabled = not enabled
            self._input_field.read_only = not enabled
        if self._send_button:
            self._send_button.disabled = not enabled

    def _set_thinking_visible(self, visible: bool) -> None:
        """Show or hide the thinking indicator."""
        if self._status_container:
            self._status_container.visible = visible

    async def main(self, page: ft.Page) -> None:
        """Main entry point for the Flet application.

        Args:
            page: The Flet page instance
        """
        self._page = page

        # Configure page
        page.title = "MCP Search Agent"
        page.window.width = self._config.window_width
        page.window.height = self._config.window_height
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = ft.Colors.SURFACE_CONTAINER_LOWEST
        page.padding = 20

        # Build theme
        page.theme = ft.Theme(
            color_scheme_seed=ft.Colors.CYAN,
        )
        page.dark_theme = ft.Theme(
            color_scheme_seed=ft.Colors.CYAN,
        )

        # Build status indicator (needs to be built before layout)
        status_indicator = self._build_status_indicator()

        # Build main layout
        main_container = ft.Container(
            content=ft.Column(
                controls=[
                    self._build_header(),
                    self._build_chat_area(),
                    status_indicator,
                    self._build_token_bar(),
                    self._build_input_area(),
                ],
                spacing=0,
                expand=True,
            ),
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border_radius=12,
            expand=True,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=15,
                color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
                offset=ft.Offset(0, 4),
            ),
        )

        page.add(main_container)
        page.update()


def run_flet_ui(
    agent: Agent,
    model_info: Optional[Any] = None,
    debug: bool = False,
) -> None:
    """Run the Flet GUI for the agent.

    Args:
        agent: The pydantic-ai agent
        model_info: Optional LanguageModelInfo for token tracking
        debug: Whether to show debug information
    """
    max_tokens = ModelInfoExtractor.get_max_tokens(model_info)
    token_tracker = TokenTracker(max_tokens=max_tokens)

    ui = FletUI(
        agent=agent,
        token_tracker=token_tracker,
        debug=debug,
    )

    ft.run(ui.main, view=ft.AppView.WEB_BROWSER)


async def _setup_agent(debug: bool = False) -> tuple[Agent, Any]:
    """Setup the agent asynchronously.

    Returns:
        Tuple of (agent, model_info)
    """
    from console_agent.agent import get_mcp_server_url
    from console_agent.console_ui import get_default_ui
    from unique_toolkit import get_async_openai_client
    from unique_toolkit.language_model import LanguageModelName

    openai_client = get_async_openai_client()
    ui = get_default_ui()

    model = LanguageModelName.AZURE_GPT_4o_2024_1120
    server_url = get_mcp_server_url()

    # Check server availability
    ui.print(f"[dim]Checking MCP server availability: {server_url}[/dim]")
    with ui.create_status("[bold yellow]Checking server...[/bold yellow]"):
        from console_agent.mcp_service import MCPService

        mcp_service = MCPService()
        connection_result = await mcp_service.check_server_available(server_url)

    ui.print_server_status(
        url=server_url,
        available=connection_result.available,
        use_oauth=True,
    )

    # Get model info
    model_info = ModelInfoExtractor.extract_from_model(model)

    # Create agent
    from console_agent.agent_factory import AgentConfig, AgentFactory

    factory = AgentFactory(openai_client)
    config = AgentConfig(
        model=str(model),
        mcp_server_url=server_url if connection_result.available else None,
        tools_available=connection_result.available,
        mcp_client=connection_result.client,
    )
    agent = factory.create(config)

    ui.print("[dim]Launching Flet GUI...[/dim]\n")

    return agent, model_info


def main_cli() -> None:
    """CLI entry point for the Flet GUI."""
    import os

    debug = os.getenv("MCP_SEARCH_DEBUG", "false").lower() in ("true", "1", "yes")

    # Run async setup first
    agent, model_info = asyncio.run(_setup_agent(debug=debug))

    # Then run sync Flet app
    run_flet_ui(agent=agent, model_info=model_info, debug=debug)
