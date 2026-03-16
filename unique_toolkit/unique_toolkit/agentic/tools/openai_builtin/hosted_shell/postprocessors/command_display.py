"""Postprocessor that displays executed shell commands in the chat.

Prepends each shell command from the model's response as a collapsible
``<details>`` block so users can inspect what was run without cluttering
the main output.
"""

import asyncio
import logging
import re
from typing import override

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from unique_toolkit.agentic.postprocessor.postprocessor_manager import (
    ResponsesApiPostprocessor,
)
from unique_toolkit.agentic.tools.config import get_configuration_dict
from unique_toolkit.language_model.schemas import ResponsesLanguageModelStreamResponse

_TEMPLATE = """
<details><summary>Shell Command</summary>

```bash
{commands}
```

</details>
</br>

""".lstrip()

logger = logging.getLogger(__name__)


class ShowExecutedCommandPostprocessorConfig(BaseModel):
    """Settings for the executed-command display postprocessor."""

    model_config = get_configuration_dict()
    remove_from_history: SkipJsonSchema[bool] = Field(
        default=True,
        description="If set, the shell command display will be removed from the history on subsequent calls.",
    )
    sleep_time_before_display: float = Field(
        default=0.2,
        description="Time to sleep before displaying the executed commands. Please increase this value if you experience rendering issues.",
    )


class ShowExecutedCommandPostprocessor(ResponsesApiPostprocessor):
    """Renders shell commands in collapsible ``<details>`` blocks.

    Inserted text is automatically stripped from message history on
    subsequent turns when ``remove_from_history`` is enabled.
    """

    def __init__(self, config: ShowExecutedCommandPostprocessorConfig):
        super().__init__(self.__class__.__name__)
        self._config = config

    @override
    async def run(self, loop_response: ResponsesLanguageModelStreamResponse) -> None:
        await asyncio.sleep(self._config.sleep_time_before_display)

    @override
    def apply_postprocessing_to_response(
        self, loop_response: ResponsesLanguageModelStreamResponse
    ) -> bool:
        prepended_text = ""
        for output in loop_response.shell_calls:
            cmds = output.commands  # property delegates to action.commands
            commands = "\n".join(cmds)
            prepended_text += _TEMPLATE.format(commands=commands)

        loop_response.message.text = prepended_text + loop_response.message.text

        return prepended_text != ""

    @override
    async def remove_from_text(self, text) -> str:
        if not self._config.remove_from_history:
            return text
        pattern = r"<details><summary>Shell Command</summary>.*?</details>"
        return re.sub(pattern, "", text, flags=re.DOTALL)
