"""Unit tests for ``unique_sdk.utils.file_io.download_content``.

These tests pin the contract of the SDK download helper:

* The new ``target_path`` kwarg routes the bytes to a caller-controlled
  destination, creating any missing parent directories. This unblocks
  callers that need the file at a specific location (e.g. inside a
  per-skill bundle directory in ``swappable_intelligence``) instead of
  the historic ``/tmp/<rand>/<filename>`` fallback.
* Omitting ``target_path`` keeps the legacy behaviour so every existing
  caller in the SDK ecosystem keeps working unchanged.
* HTTP failures are surfaced *before* we materialise the destination.
  This matters for the ``target_path`` branch: a 4xx/5xx must never
  leave a half-created directory or empty file behind on the caller's
  filesystem.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from unique_sdk.utils import file_io


def _fake_response(status_code: int = 200, content: bytes = b"hello") -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.content = content
    return response


@pytest.fixture(autouse=True)
def _sdk_globals() -> Any:
    """Make ``download_content`` self-contained: stub the package globals
    it reads so the function can build the URL/headers without needing
    real credentials. Restores them afterwards so tests stay isolated."""
    with (
        patch.object(file_io.unique_sdk, "api_base", "https://api.test"),
        patch.object(file_io.unique_sdk, "api_version", "2023-12-06"),
        patch.object(file_io.unique_sdk, "app_id", "app_test"),
        patch.object(file_io.unique_sdk, "api_key", "ukey_test"),
    ):
        yield


@pytest.mark.ai
@pytest.mark.unit
class TestDownloadContentTargetPath:
    def test_target_path_writes_bytes_to_caller_destination(
        self, tmp_path: Path
    ) -> None:
        """
        Purpose: Verify ``target_path`` routes the downloaded bytes to
            the exact caller-controlled path.
        Why this matters: Callers like ``swappable_intelligence`` need
            file_io to write into a per-skill bundle directory. The
            legacy ``/tmp/<rand>/<filename>`` fallback forced a second
            ``shutil.move`` step and was incompatible with sandboxed
            filesystems where ``/tmp`` is unavailable or unwritable.
        Setup summary: Stub ``requests.get`` with a 200 response and
            assert the bytes land at the supplied path (and not in
            ``/tmp``).
        """
        get_mock = MagicMock(return_value=_fake_response(content=b"payload"))
        target = tmp_path / "out" / "report.pdf"

        with patch.object(file_io.requests, "get", get_mock):
            result = file_io.download_content(
                companyId="company-1",
                userId="user-1",
                content_id="cont_test",
                filename="ignored.pdf",
                target_path=target,
            )

        assert result == target
        assert target.read_bytes() == b"payload"

    def test_target_path_creates_missing_parents(self, tmp_path: Path) -> None:
        """
        Purpose: Confirm parent directories are created on demand when
            ``target_path`` points into a not-yet-existing tree.
        Why this matters: Forcing callers to ``mkdir -p`` ahead of every
            download would push the same boilerplate into every
            consumer (and silently regress when one forgets). The SDK
            should make the destination usable.
        Setup summary: Pass a deeply nested ``target_path`` whose
            parents do not exist; assert the file is written and the
            tree is materialised.
        """
        get_mock = MagicMock(return_value=_fake_response(content=b"x"))
        nested = tmp_path / "a" / "b" / "c" / "file.bin"

        with patch.object(file_io.requests, "get", get_mock):
            result = file_io.download_content(
                companyId="company-1",
                userId="user-1",
                content_id="cont_test",
                filename="ignored.bin",
                target_path=str(nested),
            )

        assert Path(result) == nested
        assert nested.parent.is_dir()
        assert nested.read_bytes() == b"x"

    def test_target_path_accepts_path_and_str(self, tmp_path: Path) -> None:
        """
        Purpose: Ensure both ``str`` and ``Path`` are accepted for
            ``target_path``.
        Why this matters: Callers compose paths with both ``os.path``
            and ``pathlib``; rejecting one type would force ad-hoc
            conversions at every call site.
        Setup summary: Run the same download twice — once with a
            ``Path`` and once with an equivalent ``str`` — and assert
            both succeed and return ``Path`` objects.
        """
        get_mock = MagicMock(return_value=_fake_response(content=b"abc"))

        path_target = tmp_path / "as_path.bin"
        str_target = tmp_path / "as_str.bin"

        with patch.object(file_io.requests, "get", get_mock):
            result_path = file_io.download_content(
                companyId="company-1",
                userId="user-1",
                content_id="cont_test",
                filename="ignored.bin",
                target_path=path_target,
            )
            result_str = file_io.download_content(
                companyId="company-1",
                userId="user-1",
                content_id="cont_test",
                filename="ignored.bin",
                target_path=str(str_target),
            )

        assert isinstance(result_path, Path) and isinstance(result_str, Path)
        assert result_path == path_target
        assert result_str == str_target


@pytest.mark.ai
@pytest.mark.unit
class TestDownloadContentLegacyFallback:
    def test_no_target_path_falls_back_to_tmp(self, tmp_path: Path) -> None:
        """
        Purpose: Without ``target_path``, the SDK keeps using a fresh
            ``mkdtemp`` directory and writes ``filename`` inside it.
        Why this matters: Every existing caller in the SDK ecosystem
            depends on this fallback (CLI ``download`` command,
            toolkit's ``download_content_to_file_by_id``, integration
            tests). A regression here would silently break them.
        Setup summary: Redirect ``mkdtemp`` to ``tmp_path`` so we can
            assert the returned path lives under it; verify the bytes
            land in ``<tmp_path>/<some-dir>/<filename>``.
        """
        get_mock = MagicMock(return_value=_fake_response(content=b"legacy"))
        mkdtemp_mock = MagicMock(return_value=str(tmp_path / "rand"))
        (tmp_path / "rand").mkdir()

        with (
            patch.object(file_io.requests, "get", get_mock),
            patch.object(file_io.tempfile, "mkdtemp", mkdtemp_mock),
        ):
            result = file_io.download_content(
                companyId="company-1",
                userId="user-1",
                content_id="cont_test",
                filename="legacy.pdf",
            )

        mkdtemp_mock.assert_called_once_with(dir="/tmp")
        assert result == tmp_path / "rand" / "legacy.pdf"
        assert result.read_bytes() == b"legacy"


@pytest.mark.ai
@pytest.mark.unit
class TestDownloadContentErrors:
    def test_non_string_content_id_raises_before_request(self, tmp_path: Path) -> None:
        """
        Purpose: A non-string ``content_id`` is a programmer mistake
            and must fail fast before we hit the network.
        Why this matters: Without the guard the f-string would
            silently coerce ``None`` into the string ``"None"``, hiding
            the bug behind an opaque 404 from the gateway.
        Setup summary: Pass an integer ``content_id`` and assert
            ``ValueError`` is raised; ``requests.get`` must not be
            called.
        """
        get_mock = MagicMock()

        with (
            patch.object(file_io.requests, "get", get_mock),
            pytest.raises(ValueError, match="content_id must be a string"),
        ):
            file_io.download_content(
                companyId="company-1",
                userId="user-1",
                content_id=123,  # pyright: ignore[reportArgumentType]
                filename="ignored.pdf",
                target_path=tmp_path / "out.pdf",
            )

        get_mock.assert_not_called()

    def test_http_error_does_not_create_target_directory(self, tmp_path: Path) -> None:
        """
        Purpose: When the server returns a non-200 status, the SDK
            must raise *before* materialising the destination.
        Why this matters: Otherwise a 404/5xx would leave behind a
            half-created directory tree (and on the legacy fallback,
            even a stray ``mkdtemp`` directory) for callers who passed
            ``target_path``. That manifests as orphan empty folders in
            production.
        Setup summary: Stub the response with status 500, point
            ``target_path`` at a not-yet-existing nested path, expect
            the exception, and assert no parent directory was created.
        """
        get_mock = MagicMock(return_value=_fake_response(status_code=500))
        target = tmp_path / "should_not_exist" / "file.bin"

        with (
            patch.object(file_io.requests, "get", get_mock),
            pytest.raises(Exception, match="Status code 500"),
        ):
            file_io.download_content(
                companyId="company-1",
                userId="user-1",
                content_id="cont_test",
                filename="ignored.bin",
                target_path=target,
            )

        assert not target.exists()
        assert not target.parent.exists()

    def test_http_error_skips_legacy_tmp_directory_creation(self) -> None:
        """
        Purpose: On a non-200 response in the legacy code path, we
            must not even allocate a fresh ``mkdtemp`` directory.
        Why this matters: The user-reported bug was that errors used
            to be raised *after* ``mkdtemp`` ran, leaving stray empty
            directories under ``/tmp`` on every failed download. The
            new ordering must avoid that side effect for both branches.
        Setup summary: Stub the response with 404 and assert
            ``tempfile.mkdtemp`` is never called.
        """
        get_mock = MagicMock(return_value=_fake_response(status_code=404))
        mkdtemp_mock = MagicMock()

        with (
            patch.object(file_io.requests, "get", get_mock),
            patch.object(file_io.tempfile, "mkdtemp", mkdtemp_mock),
            pytest.raises(Exception, match="Status code 404"),
        ):
            file_io.download_content(
                companyId="company-1",
                userId="user-1",
                content_id="cont_test",
                filename="ignored.bin",
            )

        mkdtemp_mock.assert_not_called()


@pytest.mark.ai
@pytest.mark.unit
class TestDownloadContentRequestShape:
    def test_chat_id_is_appended_as_query_param(self, tmp_path: Path) -> None:
        """
        Purpose: Pinning the URL contract — when ``chat_id`` is given,
            it must be forwarded as a ``chatId`` query parameter so the
            backend resolves chat-scoped content correctly.
        Why this matters: The backend uses different ACLs for
            chat-scoped vs scope-scoped content; dropping ``chatId``
            would silently 404 on chat attachments.
        Setup summary: Capture the URL passed to ``requests.get`` and
            assert it contains ``?chatId=chat-1``.
        """
        get_mock = MagicMock(return_value=_fake_response())

        with patch.object(file_io.requests, "get", get_mock):
            file_io.download_content(
                companyId="company-1",
                userId="user-1",
                content_id="cont_test",
                filename="x.bin",
                chat_id="chat-1",
                target_path=tmp_path / "x.bin",
            )

        url = get_mock.call_args.args[0]
        assert url.endswith("/content/cont_test/file?chatId=chat-1")

    def test_auth_headers_are_forwarded(self, tmp_path: Path) -> None:
        """
        Purpose: The SDK must forward ``x-app-id``, ``x-user-id``,
            ``x-company-id``, ``x-api-version`` and ``Authorization``
            headers verbatim from ``unique_sdk`` globals + arguments.
        Why this matters: A regression here would surface as 401/403
            from the gateway and is hard to spot from a stack trace.
        Setup summary: Inspect the kwargs passed to ``requests.get``
            and assert each expected header is present with the value
            we'd expect from the test fixture.
        """
        get_mock = MagicMock(return_value=_fake_response())

        with patch.object(file_io.requests, "get", get_mock):
            file_io.download_content(
                companyId="company-1",
                userId="user-1",
                content_id="cont_test",
                filename="x.bin",
                target_path=tmp_path / "x.bin",
            )

        headers = get_mock.call_args.kwargs["headers"]
        assert headers["x-app-id"] == "app_test"
        assert headers["x-user-id"] == "user-1"
        assert headers["x-company-id"] == "company-1"
        assert headers["x-api-version"] == "2023-12-06"
        assert headers["Authorization"] == "Bearer ukey_test"
