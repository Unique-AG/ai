from string import Template

from unique_toolkit.language_model.prompt import Prompt
from unique_toolkit.language_model.schemas import LanguageModelSystemMessage

PROMPT = "System instruction: ${instruction}"
content = Template(PROMPT).substitute(instruction="Be helpful")
message = LanguageModelSystemMessage(content=content)


prompt = Prompt(PROMPT, instruction="Be helpful")
system_msg = prompt.to_user_msg_with_images([])
