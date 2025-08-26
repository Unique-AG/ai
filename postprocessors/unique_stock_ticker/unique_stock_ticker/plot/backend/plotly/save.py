import uuid
from datetime import datetime
from typing import Iterable, overload

import plotly.graph_objects as go
from unique_toolkit.content.service import ContentService


def _generate_filename(prefix: str, image_format: str):
    now = datetime.now()

    id = str(uuid.uuid4())

    formatted_time = now.strftime("%Y-%m-%d_%H-%M-%S")

    filename = f"{prefix}_{formatted_time}_{id}.{image_format}"
    return filename


def _save_plot_to_content_service(
    fig: go.Figure,
    content_service: ContentService,
    scope_id: str,
    filename: str,
    width: int | None = None,
    height: int | None = None,
    scale: float | None = None,
    image_format: str = "jpeg",
) -> str:
    image_bytes = fig.to_image(
        format=image_format, width=width, height=height, scale=scale
    )

    content = content_service.upload_content_from_bytes(
        content=image_bytes,
        content_name=filename,
        scope_id=scope_id,
        skip_ingestion=True,
        mime_type=f"image/{image_format}",
    )

    return content.id


@overload
def save_plots_to_content_service(
    figs: go.Figure,
    content_service: ContentService,
    scope_id: str,
    filename_prefix: str,
    width: int | None = None,
    height: int | None = None,
    scale: float | None = None,
    image_format: str = "jpeg",
) -> str: ...


@overload
def save_plots_to_content_service(
    figs: Iterable[go.Figure],
    content_service: ContentService,
    scope_id: str,
    filename_prefix: str,
    width: int | None = None,
    height: int | None = None,
    scale: float | None = None,
    image_format: str = "jpeg",
) -> list[str]: ...


def save_plots_to_content_service(
    figs: Iterable[go.Figure] | go.Figure,
    content_service: ContentService,
    scope_id: str,
    filename_prefix: str,
    width: int | None = None,
    height: int | None = None,
    scale: float | None = None,
    image_format: str = "jpeg",
) -> list[str] | str:
    """
    Uploads a plotly figure to the content service and returns the content id.

    Args:
        fig: The plotly figure to upload.
        content_service: The content service to upload the figure to.
        scope_id: The scope id to upload the figure to.
        filename_prefix: The prefix of the filename to upload the figure to.
                         The filename will be generated as prefix_YYYY-MM-DD_HH-MM-SS.png
        width: The width of the figure to upload.
        height: The height of the figure to upload.

    Returns:
        The content id of the uploaded figure.
    """
    is_single_fig = False
    if isinstance(figs, go.Figure):
        is_single_fig = True
        figs = [figs]

    content_ids = []
    for fig in figs:
        filename = _generate_filename(filename_prefix, image_format)
        content_ids.append(
            _save_plot_to_content_service(
                fig=fig,
                content_service=content_service,
                scope_id=scope_id,
                filename=filename,
                width=width,
                height=height,
                scale=scale,
                image_format=image_format,
            )
        )

    return content_ids[0] if is_single_fig else content_ids


def get_image_markdown_from_content_id(content_id: str) -> str:
    """
    Returns a unique markdown path for a given content id.
    """
    return f"![image](unique://content/{content_id})"
