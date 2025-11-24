from unique_sdk import LogDetail as SDKLogDetail
from unique_sdk import LogEntry as SDKLogEntry

from .schemas import LogDetail, LogEntry


def cast_log_detail(log_detail: LogDetail) -> SDKLogDetail:
    return SDKLogDetail(
        llmRequest=log_detail.llm_request.model_dump()
        if log_detail.llm_request is not None
        else None,
    )


def cast_log_entry(log_entry: LogEntry) -> SDKLogEntry:
    if log_entry.details:
        details = cast_log_detail(log_entry.details)
    else:
        details = None
    return SDKLogEntry(
        text=log_entry.text,
        createdAt=log_entry.created_at,
        actorType=log_entry.actor_type.value.upper(),
        details=details,
    )
