"""Console UI operations for the MCP Search Agent.

This module handles all Rich console output operations, following the
Single Responsibility Principle (SRP) by separating UI concerns from
business logic.
"""

import json
import sys
import traceback
from dataclasses import dataclass
from typing import Any, Optional

from rich.align import Align
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.status import Status
from rich.text import Text


@dataclass(frozen=True)
class UIConfig:
    """Configuration for UI display settings."""

    panel_width_ratio: float = 0.7
    max_panel_width: int = 70
    progress_bar_width: int = 20
    content_preview_length: int = 500


class ConsoleUI:
    """Handles all console output operations.

    Encapsulates Rich console functionality and provides a clean interface
    for displaying agent interactions, debug information, and status updates.
    """

    def __init__(
        self,
        console: Optional[Console] = None,
        config: Optional[UIConfig] = None,
    ) -> None:
        """Initialize ConsoleUI.

        Args:
            console: Optional Rich Console instance (creates new one if not provided)
            config: Optional UI configuration
        """
        self._console = console or Console()
        self._config = config or UIConfig()

    @property
    def console(self) -> Console:
        """Get the underlying Rich console."""
        return self._console

    @property
    def width(self) -> int:
        """Get the console width."""
        return self._console.width

    def _calculate_panel_width(self) -> int:
        """Calculate panel width based on console width and config."""
        return min(
            self._config.max_panel_width,
            int(self._console.width * self._config.panel_width_ratio),
        )

    def print(self, *args: Any, **kwargs: Any) -> None:
        """Print to console (passthrough to Rich console)."""
        self._console.print(*args, **kwargs)

    def print_welcome_banner(self, debug: bool = False) -> None:
        """Print a welcome banner.

        Args:
            debug: Whether debug mode is enabled
        """
        banner_text = Text("MCP Search Agent", style="bold cyan")
        subtitle = Text("Ask questions about the knowledge base", style="dim")
        help_text = Text(
            "Type 'clear', 'reset', or 'new' to start a new conversation. "
            "Type 'quit', 'exit', or 'q' to exit.",
            style="dim italic",
        )

        if debug:
            debug_text = Text(
                "🐛 Debug mode enabled - requests/responses will be shown",
                style="bold yellow",
            )
            content = f"{banner_text}\n{subtitle}\n\n{help_text}\n\n{debug_text}"
        else:
            content = f"{banner_text}\n{subtitle}\n\n{help_text}"

        self._console.print()
        self._console.print(
            Panel(
                content,
                border_style="cyan",
                padding=(1, 2),
            )
        )
        self._console.print()

    def print_user_prompt(self) -> None:
        """Print the user input prompt."""
        prompt_text = "[bold cyan]You[/bold cyan]: "
        self._console.print(prompt_text, end="")
        sys.stdout.flush()

    def clear_input_line(self) -> None:
        """Clear the input line after user enters text."""
        # Move up one line and clear it
        sys.stdout.write("\033[1A\033[K")
        sys.stdout.flush()

    def print_user_message(self, message: str) -> None:
        """Display user message in a styled panel.

        Args:
            message: The user's message to display
        """
        self._console.print()
        user_panel = Panel(
            message,
            title="[bold cyan]You[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
            width=self._calculate_panel_width(),
        )
        self._console.print(user_panel)
        self._console.print()

    def print_agent_response(self, response: str) -> None:
        """Display agent response in a right-aligned styled panel.

        Args:
            response: The agent's response (markdown supported)
        """
        agent_panel = Panel(
            Markdown(response),
            title="[bold green]Agent[/bold green]",
            border_style="green",
            padding=(1, 2),
            width=self._calculate_panel_width(),
        )
        aligned_panel = Align.right(agent_panel, width=self._console.width)
        self._console.print(aligned_panel)

    def print_tool_usage(self, tool_names: list[str]) -> None:
        """Display a compact indicator of tools used.

        Args:
            tool_names: List of tool names that were used
        """
        if not tool_names:
            return

        # Create a compact display of tools used
        tools_text = ", ".join(tool_names)
        tool_panel = Panel(
            f"[dim]{tools_text}[/dim]",
            title="[bold yellow]🔧 Tools Used[/bold yellow]",
            border_style="yellow",
            padding=(0, 1),
            width=min(50, self._calculate_panel_width()),
        )
        aligned_panel = Align.right(tool_panel, width=self._console.width)
        self._console.print(aligned_panel)

    def print_goodbye(self, interrupted: bool = False) -> None:
        """Print goodbye message.

        Args:
            interrupted: Whether the exit was due to keyboard interrupt
        """
        if interrupted:
            self._console.print("\n\n[dim]Interrupted. Goodbye![/dim]")
        else:
            self._console.print("\n[dim]Goodbye![/dim]")

    def print_history_cleared(self) -> None:
        """Print message indicating conversation history was cleared."""
        self._console.print(
            "[dim]Conversation history cleared. Token usage reset.[/dim]\n"
        )

    def print_error(self, message: str, show_traceback: bool = False) -> None:
        """Print an error message.

        Args:
            message: The error message
            show_traceback: Whether to show full traceback
        """
        self._console.print(
            f"\n[bold red]Error:[/bold red] {message}",
            style="red",
        )
        if show_traceback:
            self._console.print(
                Panel(
                    traceback.format_exc(),
                    border_style="red",
                    title="Traceback",
                )
            )

    def print_server_status(
        self,
        url: str,
        available: bool,
        use_oauth: bool = True,
    ) -> None:
        """Print MCP server status.

        Args:
            url: The server URL
            available: Whether the server is available
            use_oauth: Whether OAuth was used
        """
        self._console.print(f"[dim]Checking MCP server availability: {url}[/dim]")

        if available:
            self._console.print(
                "[bold green]✓[/bold green] MCP server is running. Tools will be available."
            )
            if use_oauth:
                self._console.print("[dim]Note: OAuth authentication completed.[/dim]")
        else:
            self._console.print(
                "[bold yellow]⚠[/bold yellow] MCP server is not available. "
                "Agent will run without search tools."
            )
            self._console.print(
                "[dim]Start the MCP server to enable knowledge base search functionality.[/dim]"
            )

    def create_status(self, message: str) -> Status:
        """Create a status spinner context manager.

        Args:
            message: The status message to display

        Returns:
            Rich Status context manager
        """
        return Status(message, console=self._console)

    def print_token_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        max_tokens: Optional[int] = None,
    ) -> None:
        """Print token usage information.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            max_tokens: Maximum tokens available (optional)
        """
        total_tokens = input_tokens + output_tokens

        if max_tokens:
            usage_text = format_token_usage(
                total_tokens,
                max_tokens,
                bar_width=self._config.progress_bar_width,
            )
            usage_percentage = (
                (total_tokens / max_tokens * 100) if max_tokens > 0 else 0
            )

            if usage_percentage >= 90:
                style = "bold red"
            elif usage_percentage >= 75:
                style = "bold yellow"
            else:
                style = "dim"

            self._console.print(f"[{style}]Token Usage: {usage_text}[/{style}]")
        else:
            self._console.print(
                f"[dim]Token Usage: {input_tokens:,} input + "
                f"{output_tokens:,} output = {total_tokens:,} total[/dim]"
            )

    def print_debug_info(self, message: str, prefix: str = "🔍 Debug:") -> None:
        """Print debug information.

        Args:
            message: The debug message
            prefix: Optional prefix for the message
        """
        self._console.print(f"[dim]{prefix} {message}[/dim]")

    def print_debug_messages(self, result: Any) -> None:
        """Print debug information about agent requests and responses.

        Args:
            result: The RunResult from the agent
        """
        messages = result.all_messages()

        self._console.print(
            "\n[bold magenta]━━━ DEBUG: Agent Messages ━━━[/bold magenta]"
        )

        for i, msg in enumerate(messages):
            msg_type = type(msg).__name__

            if msg_type == "ModelRequest":
                self._print_request_parts(i, msg)
            elif msg_type == "ModelResponse":
                self._print_response_parts(i, msg)

        self._console.print(
            "\n[bold magenta]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold magenta]\n"
        )

    def _print_request_parts(self, index: int, msg: Any) -> None:
        """Print request message parts."""
        self._console.print(f"\n[bold blue]📤 Request {index + 1}[/bold blue]")

        for part in msg.parts:
            part_type = type(part).__name__
            preview_len = self._config.content_preview_length

            if part_type == "SystemPromptPart":
                self._console.print("  [cyan]System Prompt:[/cyan]")
                self._console.print(
                    Panel(
                        part.content[:preview_len], border_style="cyan", padding=(0, 1)
                    )
                )
            elif part_type == "UserPromptPart":
                self._console.print("  [cyan]User Prompt:[/cyan]")
                self._console.print(
                    Panel(
                        part.content[:preview_len], border_style="cyan", padding=(0, 1)
                    )
                )
            elif part_type == "ToolCallPart":
                self._print_tool_call(part)
            elif part_type == "ToolReturnPart":
                self._console.print(
                    f"  [green]✅ Tool Return:[/green] [bold]{part.tool_name}[/bold]"
                )
                content_preview = str(part.content)[:preview_len]
                self._console.print(
                    Panel(content_preview, border_style="green", padding=(0, 1))
                )

    def _print_response_parts(self, index: int, msg: Any) -> None:
        """Print response message parts."""
        self._console.print(f"\n[bold green]📥 Response {index + 1}[/bold green]")

        if hasattr(msg, "usage"):
            self._console.print(
                f"  [dim]Tokens:[/dim] {msg.usage.input_tokens} input + "
                f"{msg.usage.output_tokens} output = "
                f"{msg.usage.input_tokens + msg.usage.output_tokens} total"
            )

        for part in msg.parts:
            part_type = type(part).__name__
            preview_len = self._config.content_preview_length

            if part_type == "TextPart":
                self._console.print("  [green]Text Response:[/green]")
                self._console.print(
                    Panel(
                        part.content[:preview_len], border_style="green", padding=(0, 1)
                    )
                )
            elif part_type == "ToolCallPart":
                self._print_tool_call(part)

    def _print_tool_call(self, part: Any) -> None:
        """Print a tool call part."""
        self._console.print(
            f"  [yellow]🔧 Tool Call:[/yellow] [bold]{part.tool_name}[/bold]"
        )
        args_json = json.dumps(part.args, indent=2)
        self._console.print(Panel(args_json, border_style="yellow", padding=(0, 1)))

    def print_captured_messages_on_error(self, captured_messages: list[Any]) -> None:
        """Print captured messages when an error occurs during agent run.

        Args:
            captured_messages: List of captured messages before error
        """
        self._console.print(
            "\n[bold red]🔍 Debug: Messages captured before error:[/bold red]"
        )
        for i, msg in enumerate(captured_messages):
            msg_type = type(msg).__name__
            self._console.print(f"\n[dim]Message {i + 1} ({msg_type}):[/dim]")

            if hasattr(msg, "parts"):
                for part in msg.parts:
                    part_type = type(part).__name__
                    self._console.print(f"  - {part_type}")

                    if part_type == "ToolCallPart":
                        tool_name = getattr(part, "tool_name", None)
                        if tool_name:
                            self._console.print(f"    Tool: {tool_name}")
                        args = getattr(part, "args", None)
                        if args:
                            self._console.print(
                                f"    Args: {json.dumps(args, indent=2)}"
                            )

    def print_debug_error_details(self, error: Exception) -> None:
        """Print detailed debug information about an error.

        Args:
            error: The exception that occurred
        """
        self._console.print(
            f"\n[bold red]🔍 Debug Error Details:[/bold red]\n"
            f"[red]{type(error).__name__}: {str(error)}[/red]",
            style="red",
        )
        self._console.print(
            Panel(
                traceback.format_exc(),
                border_style="red",
                title="Traceback",
            )
        )

    def print_tools_list(self, tools: list[Any], show_schema: bool = False) -> None:
        """Print available MCP tools.

        Args:
            tools: List of tool objects
            show_schema: Whether to show tool schemas
        """
        self._console.print(
            "\n[bold magenta]🔍 Debug: Available MCP tools:[/bold magenta]"
        )
        self._console.print(f"[dim]  Tool names: {[tool.name for tool in tools]}[/dim]")

        for tool in tools:
            self._console.print(
                f"[dim]  - {tool.name}: {tool.description or 'No description'}[/dim]"
            )
            if show_schema and hasattr(tool, "inputSchema") and tool.inputSchema:
                schema_str = json.dumps(tool.inputSchema, indent=2)
                self._console.print(
                    f"[dim]    Schema preview: {schema_str[:300]}...[/dim]"
                )


def format_token_usage(
    current_tokens: int,
    max_tokens: int,
    show_bar: bool = True,
    bar_width: int = 20,
) -> str:
    """Format token usage as a string with optional progress bar.

    Args:
        current_tokens: Current token usage
        max_tokens: Maximum tokens available
        show_bar: Whether to show a progress bar
        bar_width: Width of the progress bar

    Returns:
        Formatted string showing token usage
    """
    percentage = (current_tokens / max_tokens * 100) if max_tokens > 0 else 0
    usage_text = f"{current_tokens:,} / {max_tokens:,} tokens ({percentage:.1f}%)"

    if show_bar and max_tokens > 0:
        filled = int((current_tokens / max_tokens) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        return f"{usage_text}\n[{bar}]"

    return usage_text


# Module-level singleton for backward compatibility
_default_ui: Optional[ConsoleUI] = None


def get_default_ui() -> ConsoleUI:
    """Get or create the default ConsoleUI instance."""
    global _default_ui
    if _default_ui is None:
        _default_ui = ConsoleUI()
    return _default_ui
