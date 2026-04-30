"""CalVer sibling dependency pins for cycle ``*.devN`` builds.

Under PEP 440, release candidates sort **above** developmental releases on the
same patch line (``*.dev10 < *.rc1``). A floor like ``>=2026.20.0.dev6`` alone
would therefore admit an older RC published for ``2026.20.0``, which breaks
teams that RC from a divergent line.

We constrain dev floors with an RC ceiling on the **same patch triple**:

``>=YYYY.WW.P.devN,<YYYY.WW.Prc0``
"""

from __future__ import annotations

import re

_CALVER_PATCH_DEV_RE = re.compile(
    r"^(?P<release>\d{4}\.\d{2}\.\d+)\.(?P<dev>dev\d+)$",
)
# Validates dep-pin strings passed into rewrite-pyproject-pre-release.py /
# workflows: plain ``>=`` / ``==`` specs, or cycle ``*.devN`` sibling with RC cap.
_PIN_SIMPLE_SPEC = re.compile(r"^(>=|==)\d+(\.\d+)*(\.dev\d+|rc\d+)?$")
_PIN_GE_DEV_RC_CAP = re.compile(
    r"^>=(?P<rel>\d{4}\.\d{2}\.\d+)\.(?P<idev>dev\d+),\s*"
    r"<(?P<cap>\d{4}\.\d{2}\.\d+)rc\d+$",
)


def is_valid_rewrite_dep_pin(pin: str) -> bool:
    mc = _PIN_GE_DEV_RC_CAP.match(pin)
    if mc:
        return mc.group("rel") == mc.group("cap")
    return bool(_PIN_SIMPLE_SPEC.match(pin))


def dev_dependency_pin(lower_version: str) -> str:
    """Return a PEP 508 dependency suffix suitable for stamping into pyproject."""
    suffix = f">={lower_version}"
    m = _CALVER_PATCH_DEV_RE.match(lower_version)
    if m:
        suffix += f",<{m.group('release')}rc0"
    return suffix
