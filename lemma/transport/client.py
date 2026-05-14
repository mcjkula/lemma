"""HTTP client that signs every request with Epistula."""

from __future__ import annotations

import httpx
from bittensor_wallet import Keypair

from lemma.transport.epistula import sign


async def signed_post(
    client: httpx.AsyncClient,
    url: str,
    body: bytes,
    *,
    keypair: Keypair,
    signed_for_ss58: str,
    extra_headers: dict[str, str] | None = None,
    timeout_s: float | None = None,
) -> httpx.Response:
    headers = sign(keypair=keypair, body=body, signed_for_ss58=signed_for_ss58).to_http_headers()
    headers["Content-Type"] = "application/json"
    if extra_headers:
        headers.update(extra_headers)
    return await client.post(url, content=body, headers=headers, timeout=timeout_s)
