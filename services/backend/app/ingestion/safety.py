"""SSRF and crawler politeness controls.

Every network fetcher must call `assert_public_http_url` before connecting.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


class UnsafeURLError(ValueError):
    pass


def assert_public_http_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeURLError("Only http and https URLs can be fetched")
    if parsed.username or parsed.password:
        raise UnsafeURLError("URLs with credentials are not allowed")
    host = parsed.hostname
    if not host:
        raise UnsafeURLError("URL is missing a hostname")
    lowered = host.casefold()
    if lowered in {"localhost", "metadata.google.internal"} or lowered.endswith(".local"):
        raise UnsafeURLError("Host is not allowed")
    try:
        addresses = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise UnsafeURLError(f"Could not resolve host: {host}") from exc
    if not addresses:
        raise UnsafeURLError(f"Could not resolve host: {host}")
    for info in addresses:
        ip = ipaddress.ip_address(info[4][0])
        if any(ip in network for network in BLOCKED_NETWORKS):
            raise UnsafeURLError("Refusing to fetch a private or reserved address")
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise UnsafeURLError("Refusing to fetch a private or reserved address")
    return url


def content_hash(content: bytes) -> str:
    import hashlib

    return hashlib.sha256(content).hexdigest()
