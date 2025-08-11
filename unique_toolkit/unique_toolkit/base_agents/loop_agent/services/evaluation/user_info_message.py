from string import Template

HALLUCINATION_CHECK_FAILED_TEMPLATE = Template(
    """The message above contains incorrect information due to hallucination. Here are the reasons:

$hallucination_result

**Instructions**
Address the hallucinations mentioned in the message above by providing accurate information supported by a reliable source. Do not simply repeat the previous assistant's answer. If additional information is needed to resolve the hallucination, make further tool calls. If you are unable to resolve the hallucination, please indicate so."""
)

HALLUCINATION_CHECK_PASSED_TEMPLATE = Template("$hallucination_result")

EVALUATION_STATUS_MSG_TEMPLATE = Template("**$title: $status**")

EVALUATION_RESULT_MSG_TEMPLATE = Template(
    """
**$title: $evaluation_score**

<details>
  <summary><b>Reason</b></summary>
  $evaluation_score_reason
</details>
"""
)
