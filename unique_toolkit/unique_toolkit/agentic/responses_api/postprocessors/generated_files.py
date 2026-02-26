"""Deprecated: use unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors instead."""

from typing_extensions import deprecated

from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.generated_files import (
    DisplayCodeInterpreterFilesPostProcessor as _DisplayCodeInterpreterFilesPostProcessor,
)
from unique_toolkit.agentic.tools.openai_builtin.code_interpreter.postprocessors.generated_files import (
    DisplayCodeInterpreterFilesPostProcessorConfig as _DisplayCodeInterpreterFilesPostProcessorConfig,
)


@deprecated("Import from unique_toolkit.agentic.tools.openai_builtin instead")
class DisplayCodeInterpreterFilesPostProcessor(
    _DisplayCodeInterpreterFilesPostProcessor
):
    pass


@deprecated("Import from unique_toolkit.agentic.tools.openai_builtin instead")
class DisplayCodeInterpreterFilesPostProcessorConfig(
    _DisplayCodeInterpreterFilesPostProcessorConfig
):
    pass


__all__ = [
    "DisplayCodeInterpreterFilesPostProcessor",
    "DisplayCodeInterpreterFilesPostProcessorConfig",
]
