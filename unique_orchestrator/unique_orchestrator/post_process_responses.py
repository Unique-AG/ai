import re
from typing import override

from unique_toolkit.agentic.postprocessor.postprocessor_manager import Postprocessor
from unique_toolkit.language_model.schemas import ResponsesLanguageModelStreamResponse

_TEMPLATE = """
<details><summary>Code Interpreter Call</summary>    

```python
{code}
```  

</details>    
</br>

""".lstrip()


class ShowInterpreterCodePostprocessor(
    Postprocessor[ResponsesLanguageModelStreamResponse]
):
    def __init__(self):
        super().__init__(self.__class__.__name__)

    @override
    async def run(self, loop_response: ResponsesLanguageModelStreamResponse) -> str:
        return ""

    @override
    async def apply_postprocessing_to_response(
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
        # Remove code interpreter blocks using regex
        pattern = r"<details><summary>Code Interpreter Call</summary>\s*```python\s*.*?\s*```</details>"
        return re.sub(pattern, "", text, flags=re.DOTALL)
