"""Optional public IPv4 discovery for the miner axon advertisement."""

from __future__ import annotations

import ipaddress

import httpx
from loguru import logger

_IP_SOURCES: tuple[tuple[str, dict[str, str]], ...] = (
    ("https://api.ipify.org", {"format": "text"}),
    ("https://icanhazip.com", {}),
)


def discover_public_ipv4(timeout_s: float = 5.0) -> str | None:
    for url, params in _IP_SOURCES:
        try:
            r = httpx.get(url, params=params, timeout=timeout_s)
            r.raise_for_status()
            ip = r.text.strip().split()[0]
            ipaddress.IPv4Address(ip)
            return ip
        except (httpx.HTTPError, OSError, IndexError, ValueError) as e:
            logger.debug("public IPv4 discovery failed via {}: {}", url, e)
    return None
