from typing import Iterable

from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.x509 import load_pem_x509_certificate
from requests.adapters import HTTPAdapter
from urllib3.contrib.pyopenssl import (
    PyOpenSSLContext,
)
from urllib3.util.ssl_ import PROTOCOL_TLS_CLIENT


class InMemoryCertAdapter(HTTPAdapter):
    def __init__(
        self,
        cert: bytes,
        key: bytes,
        chain_certs: Iterable[bytes] | None = None,
        *args,
        **kwargs,
    ) -> None:
        self._chain_certs = tuple(chain_certs) if chain_certs else None
        self._cert = cert
        self._key = key
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        context = self._create_ssl_context()
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)

    def _create_ssl_context(self) -> PyOpenSSLContext:
        context = PyOpenSSLContext(PROTOCOL_TLS_CLIENT)
        context.set_default_verify_paths()

        context._ctx.use_certificate(load_pem_x509_certificate(self._cert))
        if self._chain_certs is not None:
            for c in self._chain_certs:
                context._ctx.add_extra_chain_cert(load_pem_x509_certificate(c))

        context._ctx.use_privatekey(
            load_pem_private_key(self._key, password=None)  # type: ignore
        )

        # Throw an exception if the private key is not valid
        context._ctx.check_privatekey()

        return context
