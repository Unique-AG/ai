from __future__ import annotations

from ipaddress import ip_address
from urllib.parse import SplitResult, urlsplit, urlunsplit


def extract_hostname(url: str) -> str | None:
    normalized_url = url.strip()
    if not normalized_url:
        return None

    hostname = urlsplit(normalized_url).hostname
    if hostname is None:
        return None

    return hostname.rstrip(".").lower()


def replace_url_host(parsed_url: SplitResult, *, host: str) -> str:
    netloc = build_netloc(
        host=host,
        port=parsed_url.port,
        username=parsed_url.username,
        password=parsed_url.password,
    )
    return urlunsplit(
        (
            parsed_url.scheme,
            netloc,
            parsed_url.path,
            parsed_url.query,
            "",
        )
    )


def build_netloc(
    host: str,
    port: int | None,
    username: str | None = None,
    password: str | None = None,
) -> str:
    credential_prefix = ""
    if username is not None:
        credential_prefix = username
        if password is not None:
            credential_prefix = f"{credential_prefix}:{password}"
        credential_prefix = f"{credential_prefix}@"

    try:
        host_ip = ip_address(host)
    except ValueError:
        normalized_host = host
    else:
        normalized_host = (
            f"[{host_ip.compressed}]" if host_ip.version == 6 else host_ip.compressed
        )

    if port is None:
        return f"{credential_prefix}{normalized_host}"

    return f"{credential_prefix}{normalized_host}:{port}"
