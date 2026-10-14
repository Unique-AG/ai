import os

import unique_sdk

SANDBOX_KB_WRITES_ENV_VAR = "UNIQUE_SDK_SANDBOX_KB_WRITES"
SANDBOX_KNOWLEDGE_BASE_PREFIX = "/sandbox-knowledge-base"

_TRUTHY_VALUES = frozenset({"1", "true", "yes"})


def sandbox_kb_writes_from_env() -> bool:
    value = os.environ.get(SANDBOX_KB_WRITES_ENV_VAR, "")
    return value.strip().lower() in _TRUTHY_VALUES


def knowledge_base_write_url(path: str) -> str:
    """Route a Knowledge Base write through the sandbox prefix when enabled.

    Only the write routes the server mirrors under
    ``/sandbox-knowledge-base`` may be passed here.
    """
    if unique_sdk.sandbox_knowledge_base_writes:
        return f"{SANDBOX_KNOWLEDGE_BASE_PREFIX}{path}"
    return path
