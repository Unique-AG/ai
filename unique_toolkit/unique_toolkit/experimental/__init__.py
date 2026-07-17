"""Experimental toolkit services.

Modules in :mod:`unique_toolkit.experimental` expose APIs that are still being
iterated on and may change without notice between minor releases. They are
intentionally not wired into :class:`~unique_toolkit.services.factory.UniqueServiceFactory`
and are not re-exported from top-level packages: import them explicitly from
their experimental subpackage.
"""

from unique_toolkit._common.streaming_deprecation import (
    install_deprecated_streaming_import_redirect,
)

install_deprecated_streaming_import_redirect()
