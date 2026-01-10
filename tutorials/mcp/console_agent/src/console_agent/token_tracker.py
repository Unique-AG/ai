"""Token usage tracking for the MCP Search Agent.

This module handles token usage tracking and model info extraction,
following the Single Responsibility Principle (SRP).
"""

from dataclasses import dataclass
from typing import Any, Optional

from console_agent.protocols import ModelInfoProtocol


@dataclass
class TokenStats:
    """Token usage statistics.

    Attributes:
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens used
    """

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Get total token count."""
        return self.input_tokens + self.output_tokens

    def add(self, input_tokens: int, output_tokens: int) -> None:
        """Add token counts.

        Args:
            input_tokens: Input tokens to add
            output_tokens: Output tokens to add
        """
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    def reset(self) -> None:
        """Reset all token counts to zero."""
        self.input_tokens = 0
        self.output_tokens = 0


class TokenTracker:
    """Tracks cumulative token usage across agent interactions.

    Provides methods for tracking token usage and calculating
    usage percentages against model limits.
    """

    def __init__(
        self,
        max_tokens: Optional[int] = None,
    ) -> None:
        """Initialize TokenTracker.

        Args:
            max_tokens: Maximum tokens available (for percentage calculations)
        """
        self._stats = TokenStats()
        self._max_tokens = max_tokens

    @property
    def input_tokens(self) -> int:
        """Get cumulative input token count."""
        return self._stats.input_tokens

    @property
    def output_tokens(self) -> int:
        """Get cumulative output token count."""
        return self._stats.output_tokens

    @property
    def total_tokens(self) -> int:
        """Get cumulative total token count."""
        return self._stats.total_tokens

    @property
    def max_tokens(self) -> Optional[int]:
        """Get maximum tokens limit."""
        return self._max_tokens

    @property
    def usage_percentage(self) -> float:
        """Get usage percentage (0-100).

        Returns:
            Usage percentage, or 0 if max_tokens is not set
        """
        if not self._max_tokens or self._max_tokens <= 0:
            return 0.0
        return (self._stats.total_tokens / self._max_tokens) * 100

    def add_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Add token usage from a single interaction.

        Args:
            input_tokens: Input tokens used
            output_tokens: Output tokens used
        """
        self._stats.add(input_tokens, output_tokens)

    def add_from_result(self, result: Any) -> None:
        """Add token usage from an agent result.

        Args:
            result: Agent run result with usage() method
        """
        usage = result.usage()
        self.add_usage(usage.input_tokens, usage.output_tokens)

    def reset(self) -> None:
        """Reset all token counts."""
        self._stats.reset()

    def is_near_limit(self, threshold: float = 0.75) -> bool:
        """Check if usage is near the limit.

        Args:
            threshold: Percentage threshold (0.0-1.0) for "near limit"

        Returns:
            True if usage percentage exceeds threshold
        """
        return self.usage_percentage >= (threshold * 100)

    def is_at_limit(self, threshold: float = 0.90) -> bool:
        """Check if usage is at or near the limit.

        Args:
            threshold: Percentage threshold (0.0-1.0) for "at limit"

        Returns:
            True if usage percentage exceeds threshold
        """
        return self.usage_percentage >= (threshold * 100)

    def get_stats(self) -> TokenStats:
        """Get a copy of current token statistics.

        Returns:
            Copy of current TokenStats
        """
        return TokenStats(
            input_tokens=self._stats.input_tokens,
            output_tokens=self._stats.output_tokens,
        )


class ModelInfoExtractor:
    """Extracts model information from various sources.

    Handles the complexity of different model info APIs and attribute
    naming conventions.
    """

    @staticmethod
    def get_max_tokens(model_info: Optional[ModelInfoProtocol]) -> Optional[int]:
        """Extract max tokens from model info.

        Tries various attribute names that different implementations might use.

        Args:
            model_info: Model information object

        Returns:
            Maximum tokens value, or None if not found
        """
        if model_info is None:
            return None

        # Try various possible attribute names
        for attr_name in ("max_tokens", "max_context", "context_window"):
            value = getattr(model_info, attr_name, None)
            if value is not None:
                return int(value)

        return None

    @staticmethod
    def extract_from_model(model: Any) -> Optional[Any]:
        """Extract LanguageModelInfo from a model or model name.

        Tries various patterns that different implementations might use.

        Args:
            model: Model instance or name

        Returns:
            LanguageModelInfo or None if extraction failed
        """
        try:
            # Pattern 1: model.get_info() method
            if hasattr(model, "get_info"):
                return model.get_info()

            # Pattern 2: model.info property
            if hasattr(model, "info"):
                return model.info

            # Pattern 3: LanguageModelInfo.get(model) static method
            try:
                from unique_toolkit.language_model.infos import LanguageModelInfo

                get_method = getattr(LanguageModelInfo, "get", None)
                if get_method is not None:
                    return get_method(model)

                # Pattern 4: LanguageModelInfo.from_name(model)
                from_name_method = getattr(LanguageModelInfo, "from_name", None)
                if from_name_method is not None:
                    return from_name_method(model)
            except ImportError:
                pass

            # Pattern 5: Direct attribute access
            return getattr(model, "info", None)

        except (AttributeError, TypeError, ValueError):
            return None


def create_tracker_from_model(model: Any) -> TokenTracker:
    """Create a TokenTracker with max_tokens from a model.

    Convenience function that extracts model info and creates a tracker.

    Args:
        model: Model instance or name

    Returns:
        TokenTracker configured with max_tokens if available
    """
    model_info = ModelInfoExtractor.extract_from_model(model)
    max_tokens = ModelInfoExtractor.get_max_tokens(model_info)
    return TokenTracker(max_tokens=max_tokens)
