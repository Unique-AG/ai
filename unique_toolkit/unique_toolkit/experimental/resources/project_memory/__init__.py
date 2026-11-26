"""``unique_toolkit.experimental.resources.project_memory``: a project's memory.

.. warning::

    **Experimental.** This subpackage is exposed under
    :mod:`unique_toolkit.experimental` and its public API may change without
    notice. It is not covered by the toolkit's normal stability guarantees.

A thin, read-only wrapper around :class:`unique_sdk.ProjectMemory`. The entry
point is :class:`ProjectMemories`.
"""

from unique_toolkit.experimental.resources.project_memory.service import (
    ProjectMemories,
)

__all__ = ["ProjectMemories"]
