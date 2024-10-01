HALLUCINATION_METRIC_SYSTEM_MSG = """
You will receive a question, references, a conversation between a user and an agent, and an output. 
The output is the answer to the question. 
Your task is to evaluate if the output is fully supported by the information provided in the references and conversation, and provide explanations on your judgement in 2 sentences.

Use the following entailment scale to generate a score:
[low] - All information in output is supported by the references/conversation, or extractions from the references/conversation.
[medium] - The output is supported by the references/conversation to some extent, but there is at least some information in the output that is not discussed in the references/conversation. For example, if an instruction asks about two concepts and the references/conversation only discusses either of them, it should be considered a [medium] hallucination level.
[high] - The output contains information that is not part of the references/conversation, is unrelated to the references/conversation, or contradicts the references/conversation.

Make sure to not use any external information/knowledge to judge whether the output is true or not. Only check whether the output is supported by the references/conversation, and not whether the output is correct or not. Also do not evaluate if the references/conversation contain further information that is not part of the output but could be relevant to the qestion.

Your answer must be in JSON format:
{
 "reason": Your explanation of your judgement of the evaluation,
 "value": decision, must be one of the following: ["high", "medium", "low"]
}                                                  
"""

HALLUCINATION_METRIC_USER_MSG = """
Here is the data:

Input:
'''
$input_text
'''

References:
'''
$contexts_text
'''

Conversation:
'''
$history_messages_text
'''

Output:
'''
$output_text
'''

Answer as JSON:
"""

HALLUCINATION_METRIC_SYSTEM_MSG_DEFAULT = """
You will receive a question and an output. 
The output is the answer to the question. 
The situation is that no references could be found to answer the question. Your task is to evaluate if the output contains any information to answer the question,
and provide a short explanations of your reasoning in 2 sentences. Also mention in your explanation that no references were provided to answer the question.

Use the following entailment scale to generate a score:
[low] - The output does not contain any information to answer the question.
[medium] - The output contains some information to answer the question, but does not answer the question entirely. 
[high] - The output answers the question.

It is not considered an answer when the output relates to the questions subject. Make sure to not use any external information/knowledge to judge whether the output is true or not. Only check that the output does not answer the question, and not whether the output is correct or not.
Your answer must be in JSON format:
{
 "reason": Your explanation of your reasoning of the evaluation,
 "value": decision, must be one of the following: ["low", "medium", "high"]
}
"""

HALLUCINATION_METRIC_USER_MSG_DEFAULT = """                                                  
Here is the data:

Input:
'''
$input_text
'''

Output:
'''
$output_text
'''

Answer as JSON:
"""
