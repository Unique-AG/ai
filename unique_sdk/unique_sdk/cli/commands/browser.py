"""Browser steering command: drive the user's signed-in Chrome tab.

``unique-cli browser <verb>`` talks to the **browser-bridge** relay service,
which forwards each action to the Unique Chrome extension over the user's
outbound WebSocket. The agent never sees the page directly — it works from the
DOM snapshot / result JSON the extension returns.

Unlike the knowledge-base commands (which hit the platform ``api_base`` via
:mod:`unique_sdk` resources), the bridge lives at its own base URL supplied by
the Swappable Intelligence runner in ``.unique-browser.json``:

    {"bridgeUrl": "https://gateway.<cluster>/browser-bridge",
     "installUrl": "https://..."}

The command therefore issues plain HTTP requests to
``{bridgeUrl}/public/browser/{status,action,control,download}`` with the same
identity headers the SDK sends (``Authorization`` / ``x-user-id`` /
``x-company-id`` / ``x-app-id``). The gateway authenticates the request and the
bridge enforces the host allowlist / kill-switch itself; the CLI only needs the
HTTP base.

Every subcommand prints a JSON envelope to stdout:

    success  -> {"ok": true, "result": <verb-specific payload>}
    failure  -> {"ok": false, "error": "<code>", "message": "...", ...}

so the agent can ``json.loads`` the output and branch on ``ok``. Error
envelopes cause a non-zero exit so Bash ``&&`` chains stop cleanly. The bridge's
``browser_not_connected`` body (installUrl + remediation) is passed through
verbatim under ``ok: false``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import requests

from unique_sdk.cli.state import ShellState

BROWSER_ERROR_PREFIX = "browser:"
BROWSER_CONFIG_FILENAME = ".unique-browser.json"
ENV_CONFIG_PATH = "UNIQUE_BROWSER_CONFIG"

# Bridge controller base (`@Controller('public/browser')`), appended to the
# configured bridge base URL. Keep in sync with the browser-bridge service.
_BRIDGE_API_PREFIX = "public/browser"

# Generous defaults: page loads / waits can legitimately take a while, and the
# bridge already caps its own per-action timeout. Downloads stream large files.
_ACTION_TIMEOUT_SECONDS = 120
_DOWNLOAD_TIMEOUT_SECONDS = 600
_DOWNLOAD_CHUNK_BYTES = 64 * 1024


class BrowserConfigError(Exception):
    """Raised when ``.unique-browser.json`` is missing or has no ``bridgeUrl``."""


def resolve_config_path(config_path: str | None = None) -> Path:
    """Locate ``.unique-browser.json`` (explicit arg → env → cwd)."""
    if config_path:
        return Path(config_path).expanduser()
    env_path = os.environ.get(ENV_CONFIG_PATH)
    if env_path:
        return Path(env_path).expanduser()
    return Path.cwd() / BROWSER_CONFIG_FILENAME


def load_browser_config(config_path: str | None = None) -> dict[str, Any]:
    """Read and validate the browser bridge config.

    Returns a dict with at least ``bridgeUrl`` (str) and an optional
    ``installUrl`` (str | None). Raises :class:`BrowserConfigError` with an
    agent-actionable message when browser control is not wired up for this
    turn, so the caller can relay it instead of dialing an empty URL.
    """
    path = resolve_config_path(config_path)
    if not path.is_file():
        raise BrowserConfigError(
            f"browser steering is not enabled for this task ({BROWSER_CONFIG_FILENAME} "
            "not found). Ask the operator to enable Browser Control on the assistant."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise BrowserConfigError(f"could not read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise BrowserConfigError(f"{path} is not a JSON object")
    bridge_url = data.get("bridgeUrl")
    if not isinstance(bridge_url, str) or not bridge_url.strip():
        raise BrowserConfigError(
            f"{path} has no 'bridgeUrl'; browser steering cannot reach the bridge."
        )
    return data


def _bridge_endpoint(bridge_url: str, endpoint: str) -> str:
    return f"{bridge_url.rstrip('/')}/{_BRIDGE_API_PREFIX}/{endpoint}"


def _auth_headers(state: ShellState, *, json_body: bool) -> dict[str, str]:
    """Identity headers mirroring ``unique_sdk`` request headers.

    On a secured cluster / localhost the gateway injects identity from the
    request context and ``api_key`` / ``app_id`` may be empty; we still send
    ``x-user-id`` / ``x-company-id`` so the bridge can key the connection.
    """
    headers: dict[str, str] = {"Accept": "application/json"}
    config = state.config
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    if config.user_id:
        headers["x-user-id"] = config.user_id
    if config.company_id:
        headers["x-company-id"] = config.company_id
    if config.app_id:
        headers["x-app-id"] = config.app_id
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def _ok(result: Any) -> str:
    return json.dumps({"ok": True, "result": result}, indent=2, ensure_ascii=False)


def _err(code: str, message: str, **extra: Any) -> str:
    body: dict[str, Any] = {"ok": False, "error": code, "message": message}
    body.update(extra)
    return json.dumps(body, indent=2, ensure_ascii=False)


def _error_from_response(resp: requests.Response) -> str:
    """Translate a non-2xx bridge response into an ``ok: false`` envelope.

    The bridge returns structured JSON bodies — ``browser_not_connected``
    (424, with ``installUrl`` + ``remediation``) and ``{error, message}`` for
    action failures. Pass those through verbatim so the agent sees the exact
    remediation the skill documents; fall back to a generic envelope when the
    body is not JSON.
    """
    try:
        body = resp.json()
    except ValueError:
        return _err(
            "browser_bridge_error",
            (resp.text or f"bridge returned HTTP {resp.status_code}").strip(),
            status=resp.status_code,
        )
    if isinstance(body, dict):
        passthrough = dict(body)
        passthrough.setdefault("error", "browser_bridge_error")
        passthrough.setdefault("message", f"bridge returned HTTP {resp.status_code}")
        passthrough["ok"] = False
        return json.dumps(passthrough, indent=2, ensure_ascii=False)
    return _err(
        "browser_bridge_error",
        f"bridge returned HTTP {resp.status_code}",
        status=resp.status_code,
    )


# ── Verb dispatch ─────────────────────────────────────────────────────────────


def cmd_browser_status(state: ShellState, *, config_path: str | None = None) -> str:
    """Probe bridge connectivity for the current user."""
    try:
        config = load_browser_config(config_path)
    except BrowserConfigError as exc:
        return _err("browser_not_configured", str(exc))

    url = _bridge_endpoint(config["bridgeUrl"], "status")
    try:
        resp = requests.get(
            url,
            headers=_auth_headers(state, json_body=False),
            timeout=_ACTION_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        return _err(
            "browser_bridge_unreachable", f"could not reach the browser bridge: {exc}"
        )
    if not resp.ok:
        return _error_from_response(resp)
    try:
        return _ok(resp.json())
    except ValueError:
        return _err("browser_bridge_error", "bridge returned a non-JSON status body")


def _post_verb(
    state: ShellState,
    endpoint: str,
    payload: dict[str, Any],
    *,
    config_path: str | None,
) -> str:
    """Shared POST for the ``action`` and ``control`` endpoints."""
    try:
        config = load_browser_config(config_path)
    except BrowserConfigError as exc:
        return _err("browser_not_configured", str(exc))

    url = _bridge_endpoint(config["bridgeUrl"], endpoint)
    try:
        resp = requests.post(
            url,
            headers=_auth_headers(state, json_body=True),
            data=json.dumps(payload),
            timeout=_ACTION_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        return _err(
            "browser_bridge_unreachable", f"could not reach the browser bridge: {exc}"
        )
    if not resp.ok:
        return _error_from_response(resp)
    try:
        body = resp.json()
    except ValueError:
        return _err("browser_bridge_error", "bridge returned a non-JSON body")
    # Controller responds with {ok: true, result}. Surface the result directly
    # under our own envelope so the shape is identical across every verb.
    if isinstance(body, dict) and "result" in body:
        return _ok(body["result"])
    return _ok(body)


def cmd_browser_action(
    state: ShellState,
    verb: str,
    args: dict[str, Any],
    *,
    tab_id: int | None = None,
    config_path: str | None = None,
) -> str:
    """Run a DOM / interaction verb against the active (or given) tab."""
    payload: dict[str, Any] = {"verb": verb, "args": args}
    if tab_id is not None:
        payload["tabId"] = tab_id
    return _post_verb(state, "action", payload, config_path=config_path)


def cmd_browser_control(
    state: ShellState,
    verb: str,
    args: dict[str, Any],
    *,
    config_path: str | None = None,
) -> str:
    """Run a control verb that steers the extension shell (panel/tab focus)."""
    payload: dict[str, Any] = {"verb": verb, "args": args}
    return _post_verb(state, "control", payload, config_path=config_path)


def cmd_browser_download(
    state: ShellState,
    url: str,
    dest: str,
    *,
    tab_id: int | None = None,
    config_path: str | None = None,
) -> str:
    """Download *url* using the page's session and stream it to *dest*.

    Writes bytes to the workspace path ``dest`` (creating parent directories).
    Does not upload to the knowledge base or attach to the chat — that is a
    separate follow-up command. Returns an envelope describing the saved file.
    """
    try:
        config = load_browser_config(config_path)
    except BrowserConfigError as exc:
        return _err("browser_not_configured", str(exc))

    payload: dict[str, Any] = {"url": url}
    if tab_id is not None:
        payload["tabId"] = tab_id

    endpoint = _bridge_endpoint(config["bridgeUrl"], "download")
    try:
        resp = requests.post(
            endpoint,
            headers=_auth_headers(state, json_body=True),
            data=json.dumps(payload),
            timeout=_DOWNLOAD_TIMEOUT_SECONDS,
            stream=True,
        )
    except requests.RequestException as exc:
        return _err(
            "browser_bridge_unreachable", f"could not reach the browser bridge: {exc}"
        )

    if not resp.ok:
        # Error bodies are small JSON — read fully (not streamed) before mapping.
        return _error_from_response(resp)

    dest_path = Path(dest).expanduser()
    if dest_path.parent and not dest_path.parent.exists():
        dest_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    try:
        with dest_path.open("wb") as handle:
            for chunk in resp.iter_content(chunk_size=_DOWNLOAD_CHUNK_BYTES):
                if chunk:
                    handle.write(chunk)
                    total += len(chunk)
    except requests.RequestException as exc:
        # Network failures during streaming (timeout, dropped connection,
        # chunked-encoding error) — drop any truncated bytes so a later step
        # can't mistake the partial file for a complete download.
        dest_path.unlink(missing_ok=True)
        return _err(
            "browser_bridge_unreachable",
            f"download stream from the browser bridge failed: {exc}",
        )
    except OSError as exc:
        dest_path.unlink(missing_ok=True)
        return _err(
            "browser_download_write_failed", f"could not write {dest_path}: {exc}"
        )

    file_name_header = resp.headers.get("X-Browser-File-Name")
    file_name = unquote(file_name_header) if file_name_header else dest_path.name
    result = {
        "path": str(dest_path),
        "bytes": total,
        "mimeType": resp.headers.get("Content-Type"),
        "fileName": file_name,
    }
    return _ok(result)


def is_error_output(output: str) -> bool:
    """Return ``True`` when a JSON envelope reports ``ok: false``.

    Lets the Click layer translate a failure envelope into a non-zero exit
    without special-casing each error code. Non-JSON or non-``ok`` payloads
    (e.g. the ``status`` body) are treated as success.
    """
    try:
        data = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return False
    return isinstance(data, dict) and data.get("ok") is False
