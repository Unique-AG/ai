from __future__ import annotations

import asyncio
import socket
from ipaddress import IPv4Network, IPv6Network, ip_address, ip_network

_TRUSTED_PRIVATE_NETWORKS: tuple[IPv4Network | IPv6Network, ...] = (
    ip_network("10.0.0.0/8"),
    ip_network("172.16.0.0/12"),
    ip_network("192.168.0.0/16"),
    ip_network("fc00::/7"),
)


def is_trusted_private_address(address: str) -> bool:
    parsed_address = ip_address(address)
    return any(parsed_address in network for network in _TRUSTED_PRIVATE_NETWORKS)


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
    *,
    allow_trusted_private: bool = False,
) -> tuple[str, str] | None:
    if not resolved_addresses:
        return (
            "dns",
            "Target host could not be resolved during safety validation",
        )

    for resolved_address in resolved_addresses:
        address = ip_address(resolved_address)
        if address.is_global:
            continue
        if allow_trusted_private and is_trusted_private_address(resolved_address):
            continue
        return (
            "private",
            "Target host resolves to a private or special-use IP address",
        )

    return None


async def resolve_and_validate_host(
    host: str,
    *,
    allow_trusted_private: bool = False,
) -> tuple[tuple[str, ...], tuple[str, str] | None]:
    try:
        resolved_addresses = await resolve_host_addresses(host)
    except socket.gaierror:
        return (), (
            "dns",
            "Target host could not be resolved during safety validation",
        )

    return resolved_addresses, block_reason_for_resolved_addresses(
        resolved_addresses,
        allow_trusted_private=allow_trusted_private,
    )


async def validate_resolved_host(host: str) -> tuple[str, str] | None:
    _, validation_error = await resolve_and_validate_host(host)
    return validation_error
