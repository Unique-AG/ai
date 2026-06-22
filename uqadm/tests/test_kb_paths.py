"""Unit tests for the shared kb path-join helper."""

from __future__ import annotations

import pytest

from uqadm.kb._paths import join_path_segments


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        # Absolute KB folder paths (kb sync): leading slash preserved.
        ("/some/path", "", "/some/path"),
        ("/some/path", "sub", "/some/path/sub"),
        ("/some/path", "a/b", "/some/path/a/b"),
        # KB root: the leading slash must survive even though rstrip empties it.
        ("/", "sub", "/sub"),
        ("/", "", ""),
        # Relative subdirs (kb download): no spurious leading slash.
        ("", "child", "child"),
        ("a/b", "child", "a/b/child"),
        ("a/b", "", "a/b"),
        # Whitespace and redundant separators are collapsed.
        (" /some/path/ ", " sub ", "/some/path/sub"),
        ("/some/path/", "/sub", "/some/path/sub"),
    ],
)
def test_join_path_segments(left: str, right: str, expected: str) -> None:
    assert join_path_segments(left, right) == expected
