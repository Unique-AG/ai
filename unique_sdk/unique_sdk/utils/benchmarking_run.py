import asyncio
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from unique_sdk.api_resources._benchmarking import Benchmarking


def _is_complete(status: Mapping[str, Any]) -> bool:
    if status.get("complete") is True or status.get("finished") is True:
        return True
    total_raw = status.get("total")
    done_raw = status.get("done")
    try:
        total = int(total_raw) if total_raw is not None else None
        done = int(done_raw) if done_raw is not None else None
    except (TypeError, ValueError):
        return False
    if total is not None and done is not None:
        return total > 0 and done >= total
    return False


async def _poll_until_done(
    user_id: str,
    company_id: str,
    poll_interval: float,
    max_wait: float,
) -> dict[str, Any]:
    max_attempts = max(1, int(max_wait // poll_interval))
    final_status: dict[str, Any] | None = None
    for _ in range(max_attempts):
        status_obj = await Benchmarking.get_status_async(user_id, company_id)
        status_dict = dict(status_obj)
        final_status = status_dict
        if _is_complete(status_dict):
            return status_dict
        await asyncio.sleep(poll_interval)
    raise TimeoutError(
        "Timed out waiting for benchmarking to complete. Last status: %r"
        % (final_status,)
    )


async def run_benchmarking_from_file(
    user_id: str,
    company_id: str,
    path_to_file: str,
    *,
    displayed_filename: str | None = None,
    force: bool | None = None,
    poll_interval: float = 5.0,
    max_wait: float = 600.0,
    save_result_to: str | None = None,
) -> dict[str, Any]:
    """
    Upload a benchmarking xlsx, poll until processing finishes,
    and optionally save the processed workbook.

    Args:
        user_id: The user ID.
        company_id: The company ID.
        path_to_file: Path to the ``.xlsx`` file to upload.
        displayed_filename: Filename sent as the multipart part (default: basename of ``path_to_file``).
        force: Optional ``force`` query flag forwarded to the upload endpoint.
        poll_interval: Seconds between status polls (default ``5.0``).
        max_wait: Maximum seconds to wait for completion (default ``600``).
        save_result_to: If set, copies the result workbook to this path after completion.

    Returns:
        A dict with ``upload``, ``status``, and optionally ``result_path``.

    Raises:
        TimeoutError: If processing does not complete within ``max_wait``.
        ValueError: If ``path_to_file`` is not an existing file.
    """
    path = Path(path_to_file)
    if not path.is_file():
        raise ValueError(f"Not a file: {path_to_file}")

    filename = displayed_filename or path.name
    file_bytes = path.read_bytes()

    upload_result = await Benchmarking.process_upload_async(
        user_id=user_id,
        company_id=company_id,
        file=file_bytes,
        filename=filename,
        force=force,
    )

    final_status = await _poll_until_done(user_id, company_id, poll_interval, max_wait)

    out: dict[str, Any] = {
        "upload": dict(upload_result),
        "status": final_status,
    }

    if save_result_to:
        tmp_path = await Benchmarking.download_processed_async(
            user_id=user_id,
            company_id=company_id,
        )
        dest = Path(save_result_to)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tmp_path, dest)
        out["result_path"] = str(dest)

    return out
