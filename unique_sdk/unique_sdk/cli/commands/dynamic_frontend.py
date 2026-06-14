from __future__ import annotations

import json
from pathlib import Path

import unique_sdk
from unique_sdk.cli.state import ShellState
from unique_sdk.utils.file_io import upload_file


def _upload_bundle(state: ShellState, file_path: str) -> str:
    path = Path(file_path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"local file not found: {file_path}")

    if not state.scope_id:
        raise ValueError("cannot upload bundle to root. cd into a folder first.")

    result = upload_file(
        userId=state.config.user_id,
        companyId=state.config.company_id,
        path_to_file=str(path),
        displayed_filename=path.name,
        mime_type="application/zip",
        scope_or_unique_path=state.scope_id,
    )
    content_id = getattr(result, "id", None)
    if not isinstance(content_id, str) or not content_id:
        raise ValueError("upload did not return a content id")
    return content_id


def _format_space(space: object) -> str:
    space_id = getattr(space, "spaceId", None) or getattr(space, "id", "")
    name = getattr(space, "name", "")
    content_id = getattr(space, "contentId", "")
    status = getattr(space, "status", None)
    phase = ""
    url = str(getattr(space, "url", "") or "")
    config_url = str(getattr(space, "configUrl", "") or "")
    if isinstance(status, dict):
        phase = str(status.get("phase") or "")
        url = url or str(status.get("url") or "")
    return "\t".join(
        part
        for part in [str(space_id), str(name), str(content_id), phase, url, config_url]
        if part
    )


def cmd_dynamic_frontend_deploy(
    state: ShellState,
    *,
    file: str | None = None,
    content_id: str | None = None,
    name: str | None = None,
    space_id: str | None = None,
    output_json: bool = False,
) -> str:
    try:
        if not file and not content_id:
            return "dynamic-frontend deploy: provide either --file or --content-id."
        if file and content_id:
            return "dynamic-frontend deploy: --file and --content-id are mutually exclusive."
        if not space_id and not name:
            return "dynamic-frontend deploy: provide --name when creating a Dynamic Frontend space."

        resolved_content_id = _upload_bundle(state, file) if file else content_id
        if not resolved_content_id:
            return "dynamic-frontend deploy: expected a content id after resolving deploy input."

        if space_id:
            update_params: unique_sdk.DynamicFrontend.UpdateParams = {
                "contentId": resolved_content_id,
            }
            if name is not None:
                update_params["name"] = name
            space = unique_sdk.DynamicFrontend.modify(
                space_id,
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                **update_params,
            )
            action = "Updated"
        else:
            space = unique_sdk.DynamicFrontend.create(
                user_id=state.config.user_id,
                company_id=state.config.company_id,
                name=name or "",
                contentId=resolved_content_id,
            )
            action = "Created"

        if output_json:
            return json.dumps(dict(space), indent=2, default=str)

        space_id_value = getattr(space, "spaceId", None) or getattr(space, "id", "")
        name_value = getattr(space, "name", name or "")
        url_value = getattr(space, "url", None)
        config_url_value = getattr(space, "configUrl", None)
        url_line = (
            f"\nURL: {url_value}" if isinstance(url_value, str) and url_value else ""
        )
        config_url_line = (
            f"\nConfig URL: {config_url_value}"
            if isinstance(config_url_value, str) and config_url_value
            else ""
        )
        return (
            f'{action} Dynamic Frontend space "{name_value}" ({space_id_value})\n'
            f"Content: {resolved_content_id}"
            f"{url_line}"
            f"{config_url_line}"
        )
    except (ValueError, unique_sdk.APIError, OSError) as e:
        return f"dynamic-frontend deploy: {e}"


def cmd_dynamic_frontend_delete(
    state: ShellState,
    space_id: str,
    *,
    output_json: bool = False,
) -> str:
    try:
        if not space_id:
            return "dynamic-frontend delete: provide a space id."
        result = unique_sdk.DynamicFrontend.delete(
            space_id,
            user_id=state.config.user_id,
            company_id=state.config.company_id,
        )
        if output_json:
            return json.dumps(dict(result), indent=2, default=str)
        deleted_id = (
            getattr(result, "spaceId", None) or getattr(result, "id", None) or space_id
        )
        return f"Deleted Dynamic Frontend space {deleted_id}"
    except (ValueError, unique_sdk.APIError) as e:
        return f"dynamic-frontend delete: {e}"


def cmd_dynamic_frontend_list(state: ShellState, *, output_json: bool = False) -> str:
    try:
        spaces = unique_sdk.DynamicFrontend.list(
            user_id=state.config.user_id,
            company_id=state.config.company_id,
        )
        if output_json:
            return json.dumps(spaces, indent=2, default=str)
        if not spaces:
            return "No manageable Dynamic Frontend spaces found."
        return "\n".join(_format_space(space) for space in spaces)
    except unique_sdk.APIError as e:
        return f"dynamic-frontend list: {e}"
