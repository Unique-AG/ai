from typing import Callable

import regex
import timeout_decorator


# Pre-compiled regex patterns for better performance
class OptimizedPatterns:
    """Pre-compiled regex patterns for efficient text cleaning."""

    # Handles nested patterns
    NESTED_IMAGES_AND_LINKS = regex.compile(
        r"!\[[^\]]*\]\(.*\)|\[[^\]]*\]\(.*\)", regex.DOTALL
    )

    # Handles non-nested patterns
    IMAGES_AND_LINKS = regex.compile(
        r"!\[[^\]]*\]\([^)]*\)|\[[^\]]*\]\([^)]*\)", regex.DOTALL
    )

    # Multiple linebreaks
    MULTIPLE_LINEBREAKS = regex.compile(r"\n{2,}")

    # Repeating patterns
    REPEATING_PATTERNS = regex.compile(r"(.{5,}?)(?:\s*\1){2,}", regex.MULTILINE)


PATTERNS = OptimizedPatterns()


def get_cleaner(pattern: regex.Pattern, timeout: float = 0.5) -> Callable[[str], str]:
    """Get a function that removes a specific pattern from text."""

    @timeout_decorator.timeout(timeout)
    def cleaner(text: str) -> str:
        return pattern.sub("", text)

    return cleaner
