"""
Test file to verify diff coverage pipeline functionality.
This file will be removed in the next commit.
"""


def untested_function():
    """This function has no tests and should trigger coverage warnings."""
    return "This function is not tested"


def another_untested_function(param: str) -> str:
    """Another function without tests."""
    if param == "test":
        return "test result"
    else:
        return "default result"


def brand_new_untested_function():
    """This is a brand new function that should trigger diff coverage."""
    return "This function was just added and has no tests"


class UntestedClass:
    """A class without any tests."""

    def __init__(self, value: int):
        self.value = value

    def multiply(self, factor: int) -> int:
        """Multiply the value by a factor."""
        return self.value * factor

    def is_positive(self) -> bool:
        """Check if the value is positive."""
        return self.value > 0


# Some module-level code that won't be covered
CONSTANT_VALUE = "uncovered constant"

if __name__ == "__main__":
    # This block won't be covered either
    obj = UntestedClass(5)
    print(f"Result: {obj.multiply(2)}")
