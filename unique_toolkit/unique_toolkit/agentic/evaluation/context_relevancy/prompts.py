CONTEXT_RELEVANCY_METRIC_SYSTEM_MSG = """
You will receive an input and a set of contexts.
Your task is to evaluate how relevant the contexts are to the input text.

Use the following rating scale to generate a score:
[low] - The contexts are not relevant to the input.
[medium] - The contexts are somewhat relevant to the input.
[high] - The contexts are highly relevant to the input.

Your answer must be in JSON format:
{
 "reason": Your explanation of your judgement of the evaluation,
 "value": decision, must be one of the following ["low", "medium", "high"]
}
"""

CONTEXT_RELEVANCY_METRIC_SYSTEM_MSG_STRUCTURED_OUTPUT = """
You will receive an input and a set of contexts.
Your task is to evaluate how relevant the contexts are to the input text. 
Further you should extract relevant facts from the contexts.

# Output Format
- Generate data according to the provided data schema.
- Ensure the output adheres to the format required by the pydantic object.
- All necessary fields should be populated as per the data schema guidelines.
"""

CONTEXT_RELEVANCY_METRIC_USER_MSG = """
Here is the data:

Input:
'''
$input_text
'''

Contexts:
'''
$context_texts
'''

Answer as JSON:
"""

CONTEXT_RELEVANCY_METRIC_USER_MSG_STRUCTURED_OUTPUT = """
Here is the data:

Input:
'''
$input_text
'''

Contexts:
'''
$context_texts
'''
"""
