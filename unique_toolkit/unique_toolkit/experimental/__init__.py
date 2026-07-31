"""Experimental toolkit services.

Modules in :mod:`unique_toolkit.experimental` expose APIs that are still being
iterated on and may change without notice between minor releases. They are
intentionally not wired into :class:`~unique_toolkit.services.factory.UniqueServiceFactory`
and are not re-exported from top-level packages: import them explicitly from
their experimental subpackage.
"""

from unique_toolkit._common.deprecated_import_redirect import (
    DeprecatedImportMapping,
    install_deprecated_import_redirect,
    register_deprecated_import_mapping,
)

_STREAMING_DEPRECATED_REMOVAL_DATE = "2026-10-17"

register_deprecated_import_mapping(
    DeprecatedImportMapping(
        old_prefix="unique_toolkit.experimental._internal.streaming",
        new_prefix="unique_toolkit._internal.streaming",
        removal_date=_STREAMING_DEPRECATED_REMOVAL_DATE,
    )
)
register_deprecated_import_mapping(
    DeprecatedImportMapping(
        old_prefix="unique_toolkit.experimental.integrations.openai.streaming",
        new_prefix="unique_toolkit.integrations.openai.streaming",
        removal_date=_STREAMING_DEPRECATED_REMOVAL_DATE,
    )
)
install_deprecated_import_redirect()
