"""Skills management — public API exports.

The data schemas (:class:`SkillInfo`, :class:`SkillVersionInfo`,
:class:`InlineSkillBundle`) are provider-agnostic.  The current
:class:`SkillService` implementation targets the OpenAI Skills API;
future providers may be supported via alternative service classes.
"""

from unique_toolkit.skills.schemas import InlineSkillBundle, SkillInfo, SkillVersionInfo
from unique_toolkit.skills.service import SkillService

__all__ = [
    "InlineSkillBundle",
    "SkillInfo",
    "SkillService",
    "SkillVersionInfo",
]
