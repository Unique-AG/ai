import logging
import re
from typing import override

from pydantic import BaseModel, Field

from unique_toolkit.agentic.postprocessor.postprocessor_manager import Postprocessor
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
    remove_from_history: bool = Field(
        default=False,
        description="If set, the code interpreter call will be removed from the history on subsequent calls to the assistant.",
    )


class ShowExecutedCodePostprocessor(
    Postprocessor[ResponsesLanguageModelStreamResponse]
):
    def __init__(self, config: ShowExecutedCodePostprocessorConfig):
        super().__init__(self.__class__.__name__)
        self._config = config

    @override
    async def run(self, loop_response: ResponsesLanguageModelStreamResponse) -> None:
        return None

    @override
    def apply_postprocessing_to_response(
        self, loop_response: ResponsesLanguageModelStreamResponse
    ) -> bool:
        prepended_text = ""
        for output in loop_response.output:
            if output.type == "code_interpreter_call":
                prepended_text += _TEMPLATE.format(code=output.code)

        loop_response.message.text = prepended_text + loop_response.message.text

        return prepended_text != ""

    @override
    async def remove_from_text(self, text) -> str:
        if not self._config.remove_from_history:
            return text
        # Remove code interpreter blocks using regex
        pattern = r"<details><summary>Code Interpreter Call</summary>.*?</details>"
        return re.sub(pattern, "", text, flags=re.DOTALL)
