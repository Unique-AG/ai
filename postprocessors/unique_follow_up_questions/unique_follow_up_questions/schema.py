from enum import StrEnum

from pydantic import BaseModel, Field


class FollowUpCategory(StrEnum):
    CLARIFICATION = "clarification"
    ELABORATION = "elaboration"
    COMPARISON = "comparison"
    IMPLICATION = "implication"
    SUMMARY = "summary"
    CONTINUATION = "continuation"
    OTHER = "other"


class FollowUpQuestion(BaseModel):
    category: FollowUpCategory = Field(
        description="The category of the follow-up question. "
        "The 'other' category should be used for questions that don't fit into the other categories."
    )
    question: str = Field(description="The follow-up question")

    @staticmethod
    def examples() -> list["FollowUpQuestion"]:
        return [
            FollowUpQuestion(
                category=FollowUpCategory.CLARIFICATION,
                question="Can you clarify the meaning of 'implied volatility'?",
            ),
            FollowUpQuestion(
                category=FollowUpCategory.ELABORATION,
                question="Can you explain more about how compound interest works over time?",
            ),
            FollowUpQuestion(
                category=FollowUpCategory.COMPARISON,
                question="How does compound interest compare to simple interest?",
            ),
            FollowUpQuestion(
                category=FollowUpCategory.IMPLICATION,
                question="If the Fed raises interest rates again, what does that mean for mortgage rates?",
            ),
            FollowUpQuestion(
                category=FollowUpCategory.SUMMARY,
                question="Can you summarize the main points of a good retirement investment strategy?",
            ),
            FollowUpQuestion(
                category=FollowUpCategory.CONTINUATION,
                question="What should I do after setting up my emergency fund?",
            ),
            FollowUpQuestion(
                category=FollowUpCategory.OTHER,
                question="Do you know any podcasts that cover personal finance topics?",
            ),
        ]


class FollowUpQuestionsOutput(BaseModel):
    questions: list[FollowUpQuestion] = Field(
        default_factory=list, description="The list of follow-up questions."
    )
