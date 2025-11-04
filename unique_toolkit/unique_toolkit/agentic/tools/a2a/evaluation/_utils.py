import logging

import unique_sdk

from unique_toolkit.chat.schemas import (
    ChatMessageAssessmentLabel,
    ChatMessageAssessmentStatus,
)

logger = logging.getLogger(__name__)

_ASSESSMENT_LABEL_COMPARISON_DICT: dict[str, int] = {
    ChatMessageAssessmentLabel.RED: 0,
    ChatMessageAssessmentLabel.YELLOW: 1,
    ChatMessageAssessmentLabel.GREEN: 2,
}


def sort_assessments(
    assessments: list[unique_sdk.Space.Assessment],
) -> list[unique_sdk.Space.Assessment]:
    return sorted(
        assessments,
        key=lambda x: _ASSESSMENT_LABEL_COMPARISON_DICT[x["label"]],  # type: ignore (should be checked before sorting)
    )


def get_worst_label(
    *labels: str,
) -> str:
    return min(
        labels,
        key=lambda x: _ASSESSMENT_LABEL_COMPARISON_DICT[x],
    )


def get_valid_assessments(
    assessments: list[unique_sdk.Space.Assessment],
    display_name: str,
    sequence_number: int,
) -> list[unique_sdk.Space.Assessment]:
    valid_assessments = []
    for assessment in assessments:
        if (
            assessment["label"] is None
            or assessment["label"] not in ChatMessageAssessmentLabel
        ):
            logger.warning(
                "Unkown assistant label %s for assistant %s (sequence number: %s) will be ignored",
                assessment["label"],
                display_name,
                sequence_number,
            )
            continue
        if assessment["status"] != ChatMessageAssessmentStatus.DONE:
            logger.warning(
                "Assessment %s for assistant %s (sequence number: %s) is not done (status: %s) will be ignored",
                assessment["label"],
                display_name,
                sequence_number,
                assessment["status"],
            )
            continue
        valid_assessments.append(assessment)

    return valid_assessments
