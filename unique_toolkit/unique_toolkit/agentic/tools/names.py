"""Canonical tool-name constants shared across toolkit modules.

This module intentionally contains only string constants so callers can depend on
stable tool identifiers without importing concrete tool classes.

TODO(UN-20578): Add canonical name constants for the remaining toolkit tools.
"""

INTERNAL_SEARCH_TOOL_NAME = "InternalSearch"
UPLOADED_SEARCH_TOOL_NAME = "UploadedSearch"
SKILL_TOOL_NAME = "Skill"
