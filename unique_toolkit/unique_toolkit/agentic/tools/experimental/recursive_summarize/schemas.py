from pydantic import BaseModel, Field


class RecursiveSummarizeInput(BaseModel):
    task_description: str = Field(
        ...,
        description=(
            "What the summary should focus on, e.g. 'Summarize the key financial risks' "
            "or 'Provide an executive summary of the uploaded contract'."
        ),
    )
    file_name: str | None = Field(
        default=None,
        description=(
            "The exact name of the single uploaded file to summarize, as shown in the "
            "chat (e.g. 'report.pdf'). Call this tool ONCE PER FILE: when several files "
            "are uploaded, make a separate call for each one, each with its own "
            "file_name. Leave empty only to summarize every uploaded file at once."
        ),
    )
    content_id: str | None = Field(
        default=None,
        description=(
            "The content id (e.g. 'cont_...') of a knowledge-base file to summarize. "
            "Obtain it from an internal search result's source id when the user asks to "
            "summarize a file that lives in the knowledge base rather than one uploaded "
            "to this chat. When provided, this exact file is summarized and 'file_name' "
            "is ignored."
        ),
    )
