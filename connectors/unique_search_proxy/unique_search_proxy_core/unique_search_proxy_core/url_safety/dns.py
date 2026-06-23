from __future__ import annotations

import asyncio
import socket
from ipaddress import ip_address


async def resolve_host_addresses(host: str) -> tuple[str, ...]:
    loop = asyncio.get_running_loop()
    resolved = await loop.run_in_executor(
        None, lambda: socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    )
    return tuple(
        dict.fromkeys(str(ip_address(sockaddr[0])) for _, _, _, _, sockaddr in resolved)
    )


def block_reason_for_resolved_addresses(
    resolved_addresses: tuple[str, ...],
) -> tuple[str, str] | None:
    if not resolved_addresses:
        return (
            "dns",
            "Target host could not be resolved during safety validation",
        )

    for resolved_address in resolved_addresses:
        if not ip_address(resolved_address).is_global:
            return (
                "private",
                "Target host resolves to a private or special-use IP address",
            )

    return None


async def resolve_and_validate_host(
    host: str,
) -> tuple[tuple[str, ...], tuple[str, str] | None]:
    try:
        resolved_addresses = await resolve_host_addresses(host)
    except socket.gaierror:
        return (), (
            "dns",
            "Target host could not be resolved during safety validation",
        )

    return resolved_addresses, block_reason_for_resolved_addresses(resolved_addresses)


async def validate_resolved_host(host: str) -> tuple[str, str] | None:
    _, validation_error = await resolve_and_validate_host(host)
    return validation_error
