"""Fixed OAuth protocol identifiers used on the wire.

These are RFC 8693 constants — not configuration. Configurable values live in
``consumer.settings``, ``producer.settings``, and ``common.clients``.
"""

from __future__ import annotations

# RFC 8693 grant + token-type identifiers.
TOKEN_EXCHANGE_GRANT = "urn:ietf:params:oauth:grant-type:token-exchange"
ACCESS_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:access_token"
