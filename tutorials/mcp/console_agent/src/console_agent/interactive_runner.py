"""Interactive runner for the MCP Search Agent.

This module handles the interactive conversation loop, following the
Single Responsibility Principle (SRP) by isolating the REPL logic.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

from pydantic_ai import Agent, capture_run_messages

from console_agent.console_ui import ConsoleUI, get_default_ui
from console_agent.token_tracker import ModelInfoExtractor, TokenTracker


class UserCommand(Enum):
    """User command types recognized by the interactive runner."""

    QUIT = auto()
    CLEAR_HISTORY = auto()
    QUESTION = auto()
    EMPTY = auto()


@dataclass
class ConversationState:
    """State of the ongoing conversation.

    Attributes:
        message_history: List of previous messages in the conversation
        token_tracker: Token usage tracker
    """

    message_history: Optional[list[Any]] = None
    token_tracker: TokenTracker = field(default_factory=TokenTracker)

    def reset(self) -> None:
        """Reset conversation state."""
        self.message_history = None
        self.token_tracker.reset()

    def update_history(self, new_messages: list[Any]) -> None:
        """Update message history with new messages.

        Args:
            new_messages: Messages to set as history
        """
        self.message_history = new_messages


class InputHandler:
    """Handles user input parsing and command detection."""

    QUIT_COMMANDS: frozenset[str] = frozenset(("quit", "exit", "q"))
    CLEAR_COMMANDS: frozenset[str] = frozenset(("clear", "reset", "new"))

    @classmethod
    def parse_input(cls, user_input: str) -> tuple[UserCommand, str]:
        """Parse user input and detect commands.

        Args:
            user_input: Raw user input string

        Returns:
            Tuple of (command type, cleaned input)
        """
        cleaned = user_input.strip()

        if not cleaned:
            return UserCommand.EMPTY, ""

        lower_input = cleaned.lower()

        if lower_input in cls.QUIT_COMMANDS:
            return UserCommand.QUIT, cleaned

        if lower_input in cls.CLEAR_COMMANDS:
            return UserCommand.CLEAR_HISTORY, cleaned

        return UserCommand.QUESTION, cleaned


class InteractiveRunner:
    """Runs the agent in an interactive conversation loop.

    Manages the REPL (Read-Eval-Print Loop) for agent interactions,
    handling user input, agent responses, and conversation state.
    """

    def __init__(
        self,
        agent: Agent,
        ui: Optional[ConsoleUI] = None,
        token_tracker: Optional[TokenTracker] = None,
        debug: bool = False,
    ) -> None:
        """Initialize InteractiveRunner.

        Args:
            agent: The pydantic-ai agent
            ui: Console UI instance (uses default if not provided)
            token_tracker: Token tracker (creates new if not provided)
            debug: Whether to show debug information
        """
        self._agent = agent
        self._ui = ui or get_default_ui()
        self._debug = debug
        self._state = ConversationState(
            token_tracker=token_tracker or TokenTracker(),
        )

    async def run(
        self,
        initial_question: Optional[str] = None,
    ) -> None:
        """Run the interactive loop.

        Args:
            initial_question: Optional initial question to ask
        """
        self._ui.print_welcome_banner(debug=self._debug)

        question = initial_question

        while True:
            try:
                result = await self._handle_iteration(question)
                question = None  # Reset for next iteration

                if result == UserCommand.QUIT:
                    break

            except KeyboardInterrupt:
                self._ui.print_goodbye(interrupted=True)
                break
            except EOFError:
                self._ui.print_goodbye()
                break
            except Exception as e:
                self._ui.print_error(str(e))
                question = None

    async def _handle_iteration(
        self,
        question: Optional[str],
    ) -> UserCommand:
        """Handle a single iteration of the interactive loop.

        Args:
            question: The question to process (None to prompt for input)

        Returns:
            The command that was processed
        """
        # Get user input if not provided
        if question is None:
            self._ui.print_user_prompt()
            raw_input = input()
            self._ui.clear_input_line()
            command, question = InputHandler.parse_input(raw_input)
        else:
            command, question = InputHandler.parse_input(question)

        # Handle special commands
        if command == UserCommand.EMPTY:
            return UserCommand.EMPTY

        if command == UserCommand.QUIT:
            self._ui.print_goodbye()
            return UserCommand.QUIT

        if command == UserCommand.CLEAR_HISTORY:
            self._state.reset()
            self._ui.print_history_cleared()
            return UserCommand.CLEAR_HISTORY

        # Process question
        await self._process_question(question)
        return UserCommand.QUESTION

    async def _process_question(self, question: str) -> None:
        """Process a user question and display the response.

        Args:
            question: The user's question
        """
        # Display user message
        self._ui.print_user_message(question)

        # Run agent with status indicator
        with self._ui.create_status("[bold yellow]Thinking...[/bold yellow]"):
            result = await self._run_agent(question)

            if result is None:
                return

        # Extract and display tool usage
        tool_names = self._extract_tool_names(result)
        self._ui.print_tool_usage(tool_names)

        # Display response
        self._ui.print_agent_response(result.output)

        # Display token usage
        self._ui.print_token_usage(
            self._state.token_tracker.input_tokens,
            self._state.token_tracker.output_tokens,
            self._state.token_tracker.max_tokens,
        )
        self._ui.print("")

    def _extract_tool_names(self, result: Any) -> list[str]:
        """Extract tool names from agent result messages.

        Args:
            result: The agent run result

        Returns:
            List of unique tool names used (in order of first use)
        """
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

    async def _run_agent(self, question: str) -> Optional[Any]:
        """Run the agent with error handling.

        Args:
            question: The user's question

        Returns:
            Agent result or None if error occurred
        """
        captured_messages: Optional[list[Any]] = None

        try:
            if self._debug:
                self._ui.print_debug_info(f"Running agent with question: {question}")
                if self._state.message_history:
                    msg_count = len(self._state.message_history)
                    self._ui.print_debug_info(
                        f"Message history has {msg_count} messages"
                    )

            # Use capture_run_messages to capture messages even if there's an error
            with capture_run_messages() as captured_messages:
                result = await self._agent.run(
                    question,
                    message_history=self._state.message_history,
                )

                # Print debug information if enabled
                if self._debug:
                    self._ui.print_debug_messages(result)

                # Update state
                self._state.update_history(result.new_messages())
                self._state.token_tracker.add_from_result(result)

                return result

        except Exception as e:
            self._handle_agent_error(e, captured_messages)
            return None

    def _handle_agent_error(
        self,
        error: Exception,
        captured_messages: Optional[list[Any]],
    ) -> None:
        """Handle an error that occurred during agent execution.

        Args:
            error: The exception that occurred
            captured_messages: Messages captured before the error
        """
        self._ui.print_error(str(error))

        if self._debug:
            if captured_messages:
                self._ui.print_captured_messages_on_error(captured_messages)
            self._ui.print_debug_error_details(error)


async def run_agent_interactive(
    agent: Agent,
    initial_question: Optional[str] = None,
    model_info: Optional[Any] = None,
    debug: bool = False,
) -> None:
    """Run the agent in an interactive loop with conversation history.

    This is a convenience function maintaining backward compatibility
    with the original API.

    Args:
        agent: The pydantic-ai agent
        initial_question: Optional initial question
        model_info: Optional LanguageModelInfo for token tracking
        debug: Whether to show debug information
    """
    # Create token tracker with model info if available
    max_tokens = ModelInfoExtractor.get_max_tokens(model_info)
    token_tracker = TokenTracker(max_tokens=max_tokens)

    runner = InteractiveRunner(
        agent=agent,
        token_tracker=token_tracker,
        debug=debug,
    )

    await runner.run(initial_question=initial_question)
