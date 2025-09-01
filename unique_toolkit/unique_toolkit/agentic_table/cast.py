from unique_sdk import LogDetail as SDKLogDetail
from unique_sdk import LogEntry as SDKLogEntry

from .schemas import LogDetail, LogEntry


def cast_log_detail(log_detail: LogDetail) -> SDKLogDetail:
    return SDKLogDetail(
        text=log_detail.text,
        messageId=log_detail.message_id,
    )


def cast_log_entry(log_entry: LogEntry) -> SDKLogEntry:
    if log_entry.details:
        details = [cast_log_detail(detail) for detail in log_entry.details]
    else:
        details = []
    return SDKLogEntry(
        text=log_entry.text,
        createdAt=log_entry.created_at,
        actorType=log_entry.actor_type.value.upper(),  # type: ignore
        messageId=log_entry.message_id,
        details=details,
    )
