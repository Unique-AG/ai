"""Query review before ``unique-cli web-search search`` (UN-29691)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

import unique_sdk
from unique_sdk._error import PermissionError as SdkPermissionError
from unique_sdk.cli.cli import main as cli_main
from unique_sdk.cli.commands.web_search import (
    QUERY_REVIEW_WAIT_TIMEOUT_SECONDS,
    USER_APPROVED_QUERIES_NOTICE,
    WEB_SEARCH_ERROR_PREFIX,
    cmd_web_search,
    cmd_web_search_many,
    is_error_output,
)
from unique_sdk.cli.config import Config
from unique_sdk.cli.identity import TURN_IDENTITY_ENV_VAR
from unique_sdk.cli.state import ShellState

pytestmark = pytest.mark.ai

_REVIEW_ON = "Web search query review is on for this space. Request a review of the queries first, then search with its reviewId."
_STILL_PENDING = "The user has not answered the web search query review yet. Wait for the answer, then search again."
_DECLINED = "The user declined the web search queries. Tell the user that the web search did not run."
_NOT_IN_TIME = "The user did not approve the web search queries in time. Tell the user that the web search did not run."
_NOT_APPROVED_QUERY = (
    'This query is not among the approved queries. Search only these: ["kept"]'
)
_PENDING_OUTPUT = (
    "The user must approve the web search queries before they are sent.\n"
    "Review id: rev_1\n"
    "Wait for the answer, then search the approved queries:\n"
    f"unique-cli elicit wait rev_1 --timeout {QUERY_REVIEW_WAIT_TIMEOUT_SECONDS}\n"
    "unique-cli web-search search --chat-id chat_1 --review-id rev_1\n"
    "Repeat any other options you used, such as --json, --include-content or -n."
)
_SECRET_QUERY = "zz-unlisted-query-should-not-leak"


def _state() -> ShellState:
    return ShellState(
        Config(
            user_id="u1",
            company_id="c1",
            api_key="key",
            app_id="app",
            api_base="https://example.com",
        )
    )


class _FakeResource:
    """Stand-in for a UniqueObject — exposes ``to_dict_recursive``."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def to_dict_recursive(self) -> dict[str, Any]:
        return self._payload


def _search_payload(query: str) -> dict[str, Any]:
    return {
        "engine": "Google",
        "query": query,
        "object": "web-search.search",
        "results": [
            {
                "url": "https://a.example",
                "title": "A",
                "snippet": "s",
                "content": "",
            }
        ],
    }


def _search_returning_its_query(**kwargs: Any) -> _FakeResource:
    return _FakeResource(_search_payload(kwargs["query"]))


def _review(
    status: str,
    *,
    review_id: str | None = "rev_1",
    queries: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "object": "web-search.review",
        "status": status,
        "reviewId": review_id,
        "queries": queries or [],
    }


def _search_rejection(status: int, message: str) -> unique_sdk.UniqueError:
    """The SDK error class the public API uses for this HTTP status."""
    if status == 409:
        return unique_sdk.APIError(message, http_status=status)
    return SdkPermissionError(message, http_status=status)


def _manifest(path: Path) -> bytes:
    if not path.exists():
        return b""
    return path.read_bytes()


@pytest.fixture(autouse=True)
def _isolate_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)


class TestReviewOffMatchesToday:
    """Output and the refs log stay byte-identical when review does not apply."""

    @patch("unique_sdk.WebSearch.search")
    @patch("unique_sdk.WebSearchReview.review")
    def test_not_required_output_matches_a_search_with_no_chat_id(
        self,
        mock_review: MagicMock,
        mock_search: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Purpose: Review-off output equals a search that never calls review.
        Why this matters: Spaces with review off, and the refs log, must not change.
        Setup summary: One search with no chat id, one with NOT_REQUIRED, separate manifests.
        """
        mock_search.side_effect = _search_returning_its_query
        mock_review.return_value = _review(
            "NOT_REQUIRED", review_id=None, queries=["q"]
        )
        plain_log = tmp_path / "plain.jsonl"
        reviewed_log = tmp_path / "reviewed.jsonl"

        plain = cmd_web_search(_state(), "q", refs_log_path=plain_log)
        reviewed = cmd_web_search(
            _state(),
            "q",
            chat_id="chat_1",
            message_id="msg_1",
            refs_log_path=reviewed_log,
        )

        assert reviewed == plain
        assert "[websource1]" in plain
        assert _manifest(plain_log) == _manifest(reviewed_log)
        assert mock_review.call_count == 1
        assert "reviewId" not in mock_search.call_args.kwargs
        assert mock_search.call_args.kwargs["chatId"] == "chat_1"

    @patch("unique_sdk.WebSearch.search")
    @patch("unique_sdk.WebSearchReview.review")
    def test_not_required_json_and_many_queries_match_no_chat_id(
        self,
        mock_review: MagicMock,
        mock_search: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Purpose: A review-off batch keeps today's JSON list and citation bytes.
        Why this matters: Agents pipe ``--json`` and cite ``[websourceN]`` from it.
        Setup summary: Two queries, JSON on, NOT_REQUIRED versus no chat id.
        """
        mock_search.side_effect = _search_returning_its_query
        mock_review.return_value = _review(
            "NOT_REQUIRED", review_id=None, queries=["git", "redis"]
        )
        plain_log = tmp_path / "plain.jsonl"
        reviewed_log = tmp_path / "reviewed.jsonl"

        plain = cmd_web_search_many(
            _state(),
            ["git", "redis"],
            output_json=True,
            refs_log_path=plain_log,
        )
        reviewed = cmd_web_search_many(
            _state(),
            ["git", "redis"],
            output_json=True,
            chat_id="chat_1",
            refs_log_path=reviewed_log,
        )

        assert reviewed == plain
        assert isinstance(json.loads(plain), list)
        assert _manifest(plain_log) == _manifest(reviewed_log)
        assert mock_review.call_count == 1
        assert mock_review.call_args.kwargs["queries"] == ["git", "redis"]
        assert all("reviewId" not in call.kwargs for call in mock_search.call_args_list)

    @patch("unique_sdk.Elicitation.get_elicitation")
    @patch("unique_sdk.WebSearchReview.review")
    @patch("unique_sdk.WebSearch.search")
    def test_no_chat_id_ignores_review_id_and_skips_review(
        self,
        mock_search: MagicMock,
        mock_review: MagicMock,
        mock_get: MagicMock,
    ) -> None:
        """Purpose: A missing chat id searches exactly as it does today.
        Why this matters: Callers outside a chat must not start a review.
        Setup summary: Pass ``review_id`` with no chat id and compare with a plain search.
        """
        mock_search.side_effect = _search_returning_its_query

        plain = cmd_web_search(_state(), "q")
        with_review_flag = cmd_web_search(_state(), "q", review_id="rev_1")

        assert with_review_flag == plain
        mock_review.assert_not_called()
        mock_get.assert_not_called()
        assert "reviewId" not in mock_search.call_args.kwargs
        assert "chatId" not in mock_search.call_args.kwargs


class TestReviewStatuses:
    @patch("unique_sdk.WebSearch.search")
    @patch("unique_sdk.WebSearchReview.review")
    def test_pending_returns_wait_instructions_and_does_not_search(
        self,
        mock_review: MagicMock,
        mock_search: MagicMock,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Purpose: A pending review tells the agent to wait, and does not search.
        Why this matters: A wait inside this command looks like a stalled turn.
        Setup summary: Review returns PENDING; assert the exact text, no manifest, no query leak.
        """
        caplog.set_level(logging.DEBUG)
        mock_review.return_value = _review("PENDING", queries=[_SECRET_QUERY])
        refs = tmp_path / "web-refs.jsonl"

        out = cmd_web_search_many(
            _state(),
            [_SECRET_QUERY, "second"],
            chat_id="chat_1",
            message_id="msg_1",
            refs_log_path=refs,
        )

        assert out == _PENDING_OUTPUT
        assert is_error_output(out) is False
        assert _SECRET_QUERY not in out
        assert _SECRET_QUERY not in caplog.text
        assert not refs.exists()
        assert not (tmp_path / ".unique" / "web-refs.jsonl").exists()
        mock_search.assert_not_called()
        mock_review.assert_called_once()
        assert mock_review.call_args.kwargs["queries"] == [_SECRET_QUERY, "second"]
        assert mock_review.call_args.kwargs["messageId"] == "msg_1"
        assert mock_review.call_args.kwargs["chatId"] == "chat_1"

    @patch("unique_sdk.WebSearch.search")
    @patch("unique_sdk.WebSearchReview.review")
    def test_retrying_a_pending_review_returns_the_same_instructions(
        self, mock_review: MagicMock, mock_search: MagicMock
    ) -> None:
        """Purpose: Asking again while the review is pending repeats the same id.
        Why this matters: The server returns the same review, and the agent must not search yet.
        Setup summary: Two identical calls against a PENDING review.
        """
        mock_review.return_value = _review("PENDING", queries=["q"])

        first = cmd_web_search(_state(), "q", chat_id="chat_1", message_id="msg_1")
        second = cmd_web_search(_state(), "q", chat_id="chat_1", message_id="msg_1")

        assert first == second == _PENDING_OUTPUT
        assert mock_review.call_count == 2
        for call in mock_review.call_args_list:
            assert call.kwargs["queries"] == ["q"]
            assert call.kwargs["chatId"] == "chat_1"
            assert call.kwargs["messageId"] == "msg_1"
            assert call.kwargs["user_id"] == "u1"
            assert call.kwargs["company_id"] == "c1"
        mock_search.assert_not_called()

    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            ("DECLINED", _DECLINED),
            ("CANCELLED", _NOT_IN_TIME),
            ("EXPIRED", _NOT_IN_TIME),
        ],
    )
    @patch("unique_sdk.WebSearch.search")
    @patch("unique_sdk.WebSearchReview.review")
    def test_terminal_status_is_an_error_and_does_not_search(
        self,
        mock_review: MagicMock,
        mock_search: MagicMock,
        status: str,
        expected: str,
        tmp_path: Path,
    ) -> None:
        """Purpose: Declined, cancelled and expired reviews do not search.
        Why this matters: The agent must tell the user the search did not run.
        Setup summary: Review returns each terminal status and an empty query list.
        """
        mock_review.return_value = _review(status, queries=[])
        refs = tmp_path / "web-refs.jsonl"

        out = cmd_web_search(
            _state(),
            "private-query-text",
            chat_id="chat_1",
            message_id="msg_1",
            refs_log_path=refs,
        )

        assert out == f"{WEB_SEARCH_ERROR_PREFIX} {expected}"
        assert "private-query-text" not in out
        assert is_error_output(out) is True
        assert not refs.exists()
        mock_search.assert_not_called()

    @patch("unique_sdk.WebSearch.search")
    @patch("unique_sdk.WebSearchReview.review")
    def test_accepted_searches_the_returned_queries_once_for_the_batch(
        self,
        mock_review: MagicMock,
        mock_search: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Purpose: An accepted review searches the user's queries, once per batch.
        Why this matters: Edited queries must be searched, and review must not run per query.
        Setup summary: Two proposed queries come back edited; assert one review and two searches.
        """
        mock_search.side_effect = _search_returning_its_query
        mock_review.return_value = _review(
            "ACCEPTED", review_id="rev_9", queries=["approved git", "approved redis"]
        )
        refs = tmp_path / "web-refs.jsonl"

        out = cmd_web_search_many(
            _state(),
            ["git", "redis"],
            chat_id="chat_1",
            message_id="msg_1",
            refs_log_path=refs,
        )

        assert out.startswith(f"{USER_APPROVED_QUERIES_NOTICE}\n\n")
        assert "'approved git'" in out
        assert "'approved redis'" in out
        assert "'git'" not in out
        assert "[websource1]" in out
        assert refs.exists()
        mock_review.assert_called_once()
        assert mock_review.call_args.kwargs["queries"] == ["git", "redis"]
        searched = [call.kwargs["query"] for call in mock_search.call_args_list]
        assert sorted(searched) == ["approved git", "approved redis"]
        assert {call.kwargs["reviewId"] for call in mock_search.call_args_list} == {
            "rev_9"
        }

    @patch("unique_sdk.WebSearch.search")
    @patch("unique_sdk.WebSearchReview.review")
    def test_accepted_single_query_keeps_single_format_and_names_the_approval(
        self, mock_review: MagicMock, mock_search: MagicMock, tmp_path: Path
    ) -> None:
        """Purpose: One approved query stays in today's single-query format, plus a notice.
        Why this matters: A one-query search must not grow a multi-query header.
        Setup summary: ACCEPTED returns the same one query; compare with a no-chat search.
        """
        mock_search.side_effect = _search_returning_its_query
        mock_review.return_value = _review("ACCEPTED", queries=["q"])
        plain_log = tmp_path / "plain.jsonl"
        approved_log = tmp_path / "approved.jsonl"

        plain = cmd_web_search(_state(), "q", refs_log_path=plain_log)
        approved = cmd_web_search(
            _state(),
            "q",
            chat_id="chat_1",
            message_id="msg_1",
            refs_log_path=approved_log,
        )

        assert approved == f"{USER_APPROVED_QUERIES_NOTICE}\n\n{plain}"
        assert "=== query" not in approved
        assert _manifest(plain_log) == _manifest(approved_log)
        assert mock_search.call_args.kwargs["reviewId"] == "rev_1"

    @patch("unique_sdk.WebSearch.search")
    @patch("unique_sdk.WebSearchReview.review")
    def test_accepted_json_carries_the_notice_and_the_same_results(
        self, mock_review: MagicMock, mock_search: MagicMock, tmp_path: Path
    ) -> None:
        """Purpose: JSON stays parseable and says the queries were user-approved.
        Why this matters: ``--json`` is piped; a text prefix would break it.
        Setup summary: ACCEPTED JSON versus the same search with no chat id.
        """
        mock_search.side_effect = _search_returning_its_query
        mock_review.return_value = _review("ACCEPTED", queries=["q"])

        plain = json.loads(
            cmd_web_search(
                _state(),
                "q",
                output_json=True,
                refs_log_path=tmp_path / "plain.jsonl",
            )
        )
        approved = json.loads(
            cmd_web_search(
                _state(),
                "q",
                output_json=True,
                chat_id="chat_1",
                refs_log_path=tmp_path / "approved.jsonl",
            )
        )

        assert approved["notice"] == USER_APPROVED_QUERIES_NOTICE
        assert approved["results"] == plain["results"]
        assert approved["results"][0]["citation"] == "websource1"

    @patch("unique_sdk.WebSearch.search")
    @patch("unique_sdk.WebSearchReview.review")
    def test_review_request_error_is_prefixed_and_does_not_search(
        self, mock_review: MagicMock, mock_search: MagicMock
    ) -> None:
        """Purpose: A failed review call is a ``web-search:`` error and does not search.
        Why this matters: Review-on without a message id must not send the queries.
        Setup summary: The review endpoint raises the server's messageId error.
        """
        mock_review.side_effect = unique_sdk.InvalidRequestError(
            "messageId is required when web search query review is on.",
            None,
            http_status=400,
        )

        out = cmd_web_search(_state(), "q", chat_id="chat_1")

        assert out == (
            f"{WEB_SEARCH_ERROR_PREFIX} messageId is required when "
            "web search query review is on."
        )
        mock_search.assert_not_called()


class TestReviewIdSearch:
    @patch("unique_sdk.Elicitation.get_elicitation")
    @patch("unique_sdk.WebSearchReview.review")
    @patch("unique_sdk.WebSearch.search")
    def test_review_id_without_queries_reads_the_elicitation(
        self,
        mock_search: MagicMock,
        mock_review: MagicMock,
        mock_get: MagicMock,
    ) -> None:
        """Purpose: ``--review-id`` with no queries searches ``responseContent.queries``.
        Why this matters: After ``elicit wait``, the agent repeats the search without retyping.
        Setup summary: Elicitation returns two approved queries; review is not called again.
        """
        mock_search.side_effect = _search_returning_its_query
        mock_get.return_value = {"responseContent": {"queries": ["from form", "also"]}}

        out = cmd_web_search_many(
            _state(), [], chat_id="chat_1", message_id="msg_1", review_id="rev_9"
        )

        assert "'from form'" in out
        assert USER_APPROVED_QUERIES_NOTICE not in out
        mock_review.assert_not_called()
        mock_get.assert_called_once()
        assert mock_get.call_args.kwargs["elicitation_id"] == "rev_9"
        assert sorted(call.kwargs["query"] for call in mock_search.call_args_list) == [
            "also",
            "from form",
        ]
        assert {call.kwargs["reviewId"] for call in mock_search.call_args_list} == {
            "rev_9"
        }

    @patch("unique_sdk.Elicitation.get_elicitation")
    @patch("unique_sdk.WebSearch.search")
    def test_review_id_with_edited_queries_sends_those_queries(
        self, mock_search: MagicMock, mock_get: MagicMock
    ) -> None:
        """Purpose: Queries passed with ``--review-id`` are searched as given.
        Why this matters: The user, or the agent, may have edited the approved wording.
        Setup summary: One edited query and a review id; the elicitation is not read.
        """
        mock_search.side_effect = _search_returning_its_query

        out = cmd_web_search(
            _state(),
            "edited query",
            chat_id="chat_1",
            review_id="rev_9",
        )

        assert "query: 'edited query'" in out
        assert "=== query" not in out
        mock_get.assert_not_called()
        assert mock_search.call_args.kwargs["query"] == "edited query"
        assert mock_search.call_args.kwargs["reviewId"] == "rev_9"

    @patch("unique_sdk.Elicitation.get_elicitation")
    @patch("unique_sdk.WebSearch.search")
    def test_review_id_without_queries_and_still_pending_does_not_search(
        self, mock_search: MagicMock, mock_get: MagicMock
    ) -> None:
        """Purpose: A review id with no answer yet repeats the wait instructions.
        Why this matters: There are no approved queries to send.
        Setup summary: The elicitation is still PENDING and has no response content.
        """
        mock_get.return_value = {"status": "PENDING", "responseContent": None}

        out = cmd_web_search_many(_state(), [], chat_id="chat_1", review_id="rev_1")

        assert out == _PENDING_OUTPUT
        assert is_error_output(out) is False
        mock_search.assert_not_called()

    @pytest.mark.parametrize(
        ("status", "message"),
        [
            (403, _REVIEW_ON),
            (409, _STILL_PENDING),
            (403, _DECLINED),
            (403, _NOT_IN_TIME),
            (403, _NOT_APPROVED_QUERY),
        ],
    )
    @patch("unique_sdk.WebSearch.search")
    def test_search_errors_keep_the_server_wording(
        self, mock_search: MagicMock, status: int, message: str
    ) -> None:
        """Purpose: Search-time review errors stay ``web-search:`` plus the server text.
        Why this matters: The agent has to repeat the server's reason, not a paraphrase.
        Setup summary: The search call raises each 403 or 409 the review contract names.
        """
        mock_search.side_effect = _search_rejection(status, message)

        out = cmd_web_search(_state(), "q", chat_id="chat_1", review_id="rev_1")

        assert out == f"{WEB_SEARCH_ERROR_PREFIX} {message}"


class TestWebSearchReviewResource:
    @patch("unique_sdk.api_resources._web_search.WebSearchReview._static_request")
    def test_review_posts_the_review_endpoint(self, mock_request: MagicMock) -> None:
        """Purpose: ``WebSearchReview.review`` posts ``/web-search-api/review``.
        Why this matters: The CLI and other SDK callers share this one resource.
        Setup summary: Patch the static request and inspect the URL and body.
        """
        mock_request.return_value = _review("NOT_REQUIRED", queries=["q"])

        unique_sdk.WebSearchReview.review(
            user_id="u",
            company_id="c",
            chatId="chat_1",
            messageId="msg_1",
            queries=["q"],
        )

        method, url, *_rest = mock_request.call_args[0]
        assert method == "post"
        assert url == "/web-search-api/review"
        assert mock_request.call_args.kwargs["params"] == {
            "chatId": "chat_1",
            "messageId": "msg_1",
            "queries": ["q"],
        }

    @patch(
        "unique_sdk.api_resources._web_search.WebSearchReview._static_request_async",
        new_callable=AsyncMock,
    )
    async def test_review_async_posts_the_review_endpoint(
        self, mock_request: AsyncMock
    ) -> None:
        """Purpose: ``review_async`` posts the same review endpoint.
        Why this matters: Async callers need the same contract as ``review``.
        Setup summary: Patch the async static request and await ``review_async``.
        """
        mock_request.return_value = _review("PENDING", queries=["q"])

        await unique_sdk.WebSearchReview.review_async(
            user_id="u",
            company_id="c",
            chatId="chat_1",
            queries=["q"],
        )

        method, url, *_rest = mock_request.call_args[0]
        assert method == "post"
        assert url == "/web-search-api/review"

    def test_review_object_name_is_registered(self) -> None:
        """Purpose: The review object name routes responses to ``WebSearchReview``.
        Why this matters: The SDK builds the typed object from ``object``.
        Setup summary: Read ``OBJECT_NAME`` and the object-class table.
        """
        from unique_sdk._object_classes import OBJECT_CLASSES

        assert unique_sdk.WebSearchReview.OBJECT_NAME == "web-search.review"
        assert OBJECT_CLASSES["web-search.review"] is unique_sdk.WebSearchReview


class TestClickQueryReview:
    def _bootstrap_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("UNIQUE_USER_ID", "u1")
        monkeypatch.setenv("UNIQUE_COMPANY_ID", "c1")
        monkeypatch.setenv("UNIQUE_API_KEY", "ukey_test")
        monkeypatch.setenv("UNIQUE_APP_ID", "app_test")
        monkeypatch.delenv("UNIQUE_CHAT_ID", raising=False)
        monkeypatch.delenv("UNIQUE_MESSAGE_ID", raising=False)
        monkeypatch.delenv(TURN_IDENTITY_ENV_VAR, raising=False)

    def test_help_explains_pending_wait_and_declined(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Purpose: Command help tells the agent what to do with a review.
        Why this matters: The pending output points at the same wait-then-search steps.
        Setup summary: Invoke ``web-search search --help``.
        """
        self._bootstrap_env(monkeypatch)

        result = CliRunner().invoke(cli_main, ["web-search", "search", "--help"])

        assert result.exit_code == 0
        assert "--review-id" in result.output
        assert "elicit wait" in result.output
        assert f"--timeout {QUERY_REVIEW_WAIT_TIMEOUT_SECONDS}" in result.output
        assert "did not run" in result.output

    def test_missing_queries_stay_a_usage_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Purpose: Search with no queries and no review id is still a usage error.
        Why this matters: Making queries optional must not turn a typo into a search.
        Setup summary: Invoke ``web-search search`` with no arguments.
        """
        self._bootstrap_env(monkeypatch)

        result = CliRunner().invoke(cli_main, ["web-search", "search"])

        assert result.exit_code == 2

    @patch("unique_sdk.WebSearch.search")
    @patch("unique_sdk.WebSearchReview.review")
    def test_chat_passes_message_id_and_review_off_output_is_unchanged(
        self,
        mock_review: MagicMock,
        mock_search: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Purpose: The CLI reads the message id and still prints today's results when review is off.
        Why this matters: Conduct sets ``UNIQUE_MESSAGE_ID``; review-off output must not change.
        Setup summary: Env chat and message ids, review returns NOT_REQUIRED, compare two invokes.
        """
        self._bootstrap_env(monkeypatch)
        mock_search.side_effect = _search_returning_its_query
        mock_review.return_value = _review(
            "NOT_REQUIRED", review_id=None, queries=["q"]
        )
        runner = CliRunner()

        without_chat = runner.invoke(cli_main, ["web-search", "search", "q"])
        monkeypatch.setenv("UNIQUE_CHAT_ID", "chat_1")
        monkeypatch.setenv("UNIQUE_MESSAGE_ID", "msg_1")
        with_chat = runner.invoke(cli_main, ["web-search", "search", "q"])

        assert without_chat.exit_code == 0
        assert with_chat.exit_code == 0
        assert with_chat.output == without_chat.output
        assert mock_review.call_count == 1
        assert mock_review.call_args.kwargs["messageId"] == "msg_1"
        reviewed_call = mock_search.call_args_list[-1].kwargs
        assert reviewed_call["chatId"] == "chat_1"
        assert "messageId" not in reviewed_call
        assert "reviewId" not in reviewed_call
        assert "chatId" not in mock_search.call_args_list[0].kwargs

    @patch("unique_sdk.Elicitation.get_elicitation")
    @patch("unique_sdk.WebSearch.search")
    def test_review_id_without_queries_is_accepted(
        self,
        mock_search: MagicMock,
        mock_get: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Purpose: ``--review-id`` alone is a valid search command.
        Why this matters: The wait step's next command has no positional queries.
        Setup summary: Invoke search with only ``--review-id`` and a chat id.
        """
        self._bootstrap_env(monkeypatch)
        monkeypatch.setenv("UNIQUE_CHAT_ID", "chat_1")
        mock_search.side_effect = _search_returning_its_query
        mock_get.return_value = {"responseContent": {"queries": ["approved"]}}

        result = CliRunner().invoke(
            cli_main, ["web-search", "search", "--review-id", "rev_9"]
        )

        assert result.exit_code == 0
        assert "query: 'approved'" in result.output
        assert mock_search.call_args.kwargs["reviewId"] == "rev_9"
        assert mock_search.call_args.kwargs["query"] == "approved"

    @patch("unique_sdk.Elicitation.get_elicitation")
    @patch("unique_sdk.WebSearch.search")
    def test_review_id_with_an_edited_query(
        self,
        mock_search: MagicMock,
        mock_get: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Purpose: A query typed after ``--review-id`` is the one that is searched.
        Why this matters: The user may have edited the query in the form.
        Setup summary: Invoke search with ``--review-id`` and one positional query.
        """
        self._bootstrap_env(monkeypatch)
        monkeypatch.setenv("UNIQUE_CHAT_ID", "chat_1")
        mock_search.side_effect = _search_returning_its_query

        result = CliRunner().invoke(
            cli_main,
            ["web-search", "search", "--review-id", "rev_9", "edited query"],
        )

        assert result.exit_code == 0
        assert "query: 'edited query'" in result.output
        mock_get.assert_not_called()
        assert mock_search.call_args.kwargs["query"] == "edited query"
        assert mock_search.call_args.kwargs["reviewId"] == "rev_9"

    @patch("unique_sdk.Elicitation.get_elicitation")
    @patch("unique_sdk.WebSearch.search")
    def test_resume_json_shape_follows_the_approved_query_count(
        self,
        mock_search: MagicMock,
        mock_get: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Purpose: A resume with one approved query returns the single-query JSON object.
        Why this matters: The documented ``.results[].url`` pipeline needs an object, not a list.
        Setup summary: Resume with ``--json`` against one, then two approved queries.
        """
        self._bootstrap_env(monkeypatch)
        monkeypatch.setenv("UNIQUE_CHAT_ID", "chat_1")
        mock_search.side_effect = _search_returning_its_query
        args = ["web-search", "search", "--json", "--review-id", "rev_9"]

        mock_get.return_value = {"responseContent": {"queries": ["only"]}}
        one = CliRunner().invoke(cli_main, args)
        mock_get.return_value = {"responseContent": {"queries": ["a", "b"]}}
        two = CliRunner().invoke(cli_main, args)

        assert isinstance(json.loads(one.output), dict)
        assert isinstance(json.loads(two.output), list)

    @patch("unique_sdk.Elicitation.get_elicitation")
    @patch("unique_sdk.WebSearch.search")
    def test_resume_does_not_need_a_readable_turn_identity(
        self,
        mock_search: MagicMock,
        mock_get: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Purpose: Resuming with ``--review-id`` never reads the message id.
        Why this matters: A broken turn-identity file must not block a search that can run.
        Setup summary: Point the identity file at a missing path and resume with an explicit chat.
        """
        self._bootstrap_env(monkeypatch)
        monkeypatch.setenv(TURN_IDENTITY_ENV_VAR, str(tmp_path / "missing.json"))
        mock_search.side_effect = _search_returning_its_query
        mock_get.return_value = {"responseContent": {"queries": ["approved"]}}

        result = CliRunner().invoke(
            cli_main,
            ["web-search", "search", "--chat-id", "chat_1", "--review-id", "rev_9"],
        )

        assert result.exit_code == 0
        assert mock_search.call_args.kwargs["reviewId"] == "rev_9"

    @patch("unique_sdk.WebSearch.search")
    @patch("unique_sdk.WebSearchReview.review")
    def test_pending_exits_zero_and_declined_exits_one(
        self,
        mock_review: MagicMock,
        mock_search: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Purpose: Pending is success output; declined is an error exit.
        Why this matters: The agent must keep going on pending and stop on declined.
        Setup summary: Two CLI invokes, one PENDING and one DECLINED.
        """
        self._bootstrap_env(monkeypatch)
        monkeypatch.setenv("UNIQUE_CHAT_ID", "chat_1")
        monkeypatch.setenv("UNIQUE_MESSAGE_ID", "msg_1")
        runner = CliRunner()
        mock_review.return_value = _review("PENDING", queries=["q"])

        pending = runner.invoke(cli_main, ["web-search", "search", "q"])
        mock_review.return_value = _review("DECLINED", queries=[])
        declined = runner.invoke(cli_main, ["web-search", "search", "q"])

        assert pending.exit_code == 0
        assert pending.output == _PENDING_OUTPUT + "\n"
        assert declined.exit_code == 1
        assert declined.output == f"{WEB_SEARCH_ERROR_PREFIX} {_DECLINED}\n"
        mock_search.assert_not_called()
