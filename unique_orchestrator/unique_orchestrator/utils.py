from __future__ import annotations

from unique_toolkit.agentic.feature_flags import feature_flags
from unique_toolkit.app.schemas import ChatEventAdditionalParameters
from unique_toolkit.content import Content


def filter_uploaded_documents_by_selection(
    documents: list[Content],
    additional_parameters: ChatEventAdditionalParameters | None,
    company_id: str,
) -> list[Content]:
    """Return only the documents the user has actively selected.

    Returns *all* documents unchanged when:
    - the feature flag is disabled for ``company_id``,
    - ``additional_parameters`` is ``None``.
    """
    if not feature_flags.enable_selected_uploaded_files_un_18470.is_enabled(company_id):
        return documents

    if additional_parameters is None:
        return documents

    selected_ids = additional_parameters.selected_uploaded_file_ids
    return [doc for doc in documents if doc.id in selected_ids]
