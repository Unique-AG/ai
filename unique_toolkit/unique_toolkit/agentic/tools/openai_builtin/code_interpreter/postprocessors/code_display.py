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
<details><summary>Code Interpreter Call</summary>    

```python
{code}
```  

</details>    
</br>

""".lstrip()


logger = logging.getLogger(__name__)


class ShowExecutedCodePostprocessorConfig(BaseModel):
    model_config = get_configuration_dict()
    enable: bool = Field(
        default=True,
        description="Show the executed source code to the user",
    )
    enable_code_execution_fence: bool = Field(
        default=True,
        description=(
            "Show generated files as interactive cards with a built-in code view "
            "and hide the legacy collapsible code block below."
        ),
    )
    enable_html_with_fence: bool = Field(
        default=True,
        description=(
            "Show generated HTML files as interactive cards with a built-in code "
            "view instead of a plain rendered HTML block. Has no effect on its "
            "own: 'enable_code_execution_fence' must be on as well. While that "
            "switch is off, HTML files stay a plain rendered HTML block."
        ),
    )
    remove_from_history: SkipJsonSchema[bool] = (
        Field(  # At the moment, it's not possible to keep executed code in the history
            default=True,
            description="If set, the code interpreter call will be removed from the history on subsequent calls to the assistant.",
        )
    )
    sleep_time_before_display: float = Field(
        default=0.2,
        description="Time to sleep before displaying the executed code. Please increase this value if you experience rendering issues.",
    )


class ShowExecutedCodePostprocessor(ResponsesApiPostprocessor):
    def __init__(
        self,
        config: ShowExecutedCodePostprocessorConfig,
    ):
        super().__init__(self.__class__.__name__)
        self._config = config
        # When fences are enabled, the fence itself shows the executed code,
        # so this legacy <details> display must stay off.
        self._is_enabled = config.enable and not config.enable_code_execution_fence

    @override
    async def run(self, loop_response: ResponsesLanguageModelStreamResponse) -> None:
        if self._is_enabled:
            await asyncio.sleep(self._config.sleep_time_before_display)

    @override
    def apply_postprocessing_to_response(
        self, loop_response: ResponsesLanguageModelStreamResponse
    ) -> bool:
        if not self._is_enabled:
            return False

        prepended_text = ""
        for output in loop_response.code_interpreter_calls:
            prepended_text += _TEMPLATE.format(code=output.code)

        loop_response.message.text = prepended_text + (loop_response.message.text or "")

        return prepended_text != ""

    @override
    async def remove_from_text(self, text) -> str:
        if not self._config.remove_from_history:
            return text
        pattern = r"<details><summary>Code Interpreter Call</summary>.*?</details>"
        return re.sub(pattern, "", text, flags=re.DOTALL)
