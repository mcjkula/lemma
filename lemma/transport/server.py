"""FastAPI dependency that verifies Epistula-signed requests."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Request

from lemma.common.config import LemmaSettings
from lemma.transport.epistula import EpistulaHeaders, ReplayCache, verify

_REPLAY_CACHE = ReplayCache()
_MAX_CHARS = LemmaSettings().lemma_inbound_max_chars


@dataclass(frozen=True, slots=True)
class RequestContext:
    sender_ss58: str
    body: bytes


async def verify_epistula(request: Request, receiver_ss58: str) -> RequestContext:
    body = await request.body()
    if _MAX_CHARS > 0 and len(body) > _MAX_CHARS:
        raise HTTPException(status_code=413, detail=f"body exceeds {_MAX_CHARS} chars")
    headers = EpistulaHeaders.from_http_headers(dict(request.headers))
    if headers is None:
        raise HTTPException(status_code=401, detail="epistula: missing_headers")
    outcome = verify(headers=headers, body=body, receiver_ss58=receiver_ss58, replay_cache=_REPLAY_CACHE)
    if not outcome.ok:
        raise HTTPException(status_code=401, detail=f"epistula: {outcome.reason}")
    return RequestContext(sender_ss58=headers.signed_by, body=body)
