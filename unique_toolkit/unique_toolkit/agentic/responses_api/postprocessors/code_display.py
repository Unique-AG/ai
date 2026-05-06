"""Deprecated: use unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors instead."""

from typing_extensions import deprecated

from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.code_display import (
    ShowExecutedCodePostprocessor as _ShowExecutedCodePostprocessor,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.code_display import (
    ShowExecutedCodePostprocessorConfig as _ShowExecutedCodePostprocessorConfig,
)


@deprecated("Import from unique_toolkit.agentic.tools.openai_builtin instead")
class ShowExecutedCodePostprocessor(_ShowExecutedCodePostprocessor):
    pass


@deprecated("Import from unique_toolkit.agentic.tools.openai_builtin instead")
class ShowExecutedCodePostprocessorConfig(_ShowExecutedCodePostprocessorConfig):
    pass


__all__ = [
    "ShowExecutedCodePostprocessor",
    "ShowExecutedCodePostprocessorConfig",
]
