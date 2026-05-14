"""FastAPI dependency that verifies Epistula-signed requests."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, Request

from lemma.transport.epistula import EpistulaHeaders, ReplayCache, verify

_REPLAY_CACHE = ReplayCache()


@dataclass(frozen=True, slots=True)
class RequestContext:
    sender_ss58: str
    body: bytes


async def verify_epistula(
    request: Request,
    receiver_ss58: str,
    epistula_version: str = Header(..., alias="Epistula-Version"),
    epistula_timestamp: str = Header(..., alias="Epistula-Timestamp"),
    epistula_uuid: str = Header(..., alias="Epistula-Uuid"),
    epistula_signed_for: str = Header(..., alias="Epistula-Signed-For"),
    epistula_signed_by: str = Header(..., alias="Epistula-Signed-By"),
    epistula_signature: str = Header(..., alias="Epistula-Request-Signature"),
) -> RequestContext:
    body = await request.body()
    headers = EpistulaHeaders(
        version=epistula_version,
        timestamp_ms=epistula_timestamp,
        uuid=epistula_uuid,
        signed_for=epistula_signed_for,
        signed_by=epistula_signed_by,
        signature_hex=epistula_signature,
    )
    outcome = verify(
        headers=headers,
        body=body,
        receiver_ss58=receiver_ss58,
        replay_cache=_REPLAY_CACHE,
    )
    if not outcome.ok:
        raise HTTPException(status_code=401, detail=f"epistula: {outcome.reason}")
    return RequestContext(sender_ss58=headers.signed_by, body=body)
