"""Default FASTMCP_CHECK_FOR_UPDATES=off; sync live settings if already loaded."""

from __future__ import annotations

import os
import sys

os.environ.setdefault("FASTMCP_CHECK_FOR_UPDATES", "off")
_fastmcp = sys.modules.get("fastmcp")
if _fastmcp is not None:
    _fastmcp.settings.check_for_updates = os.environ["FASTMCP_CHECK_FOR_UPDATES"]
