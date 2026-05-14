"""Epistula signed-header transport.

Per knowledge/sdk.quick_reference.yaml:292-326. The signature covers
``sha256(<timestamp_ms>.<nonce>.<sender>.<receiver>.<body>)``; verifiers reject
stale timestamps and replayed nonces.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Final

from bittensor_wallet import Keypair  # ships transitively via bittensor

EPISTULA_VERSION: Final[str] = "2"
DEFAULT_TIMESTAMP_SKEW_MS: Final[int] = 60_000
REPLAY_CACHE_MAX: Final[int] = 4096


@dataclass(frozen=True, slots=True)
class EpistulaHeaders:
    version: str
    timestamp_ms: str
    uuid: str
    signed_for: str
    signed_by: str
    signature_hex: str

    def to_http_headers(self) -> dict[str, str]:
        return {
            "Epistula-Version": self.version,
            "Epistula-Timestamp": self.timestamp_ms,
            "Epistula-Uuid": self.uuid,
            "Epistula-Signed-For": self.signed_for,
            "Epistula-Signed-By": self.signed_by,
            "Epistula-Request-Signature": self.signature_hex,
        }

    @classmethod
    def from_http_headers(cls, h: dict[str, str]) -> EpistulaHeaders | None:
        lower = {k.lower(): v for k, v in h.items()}
        try:
            return cls(
                version=lower["epistula-version"],
                timestamp_ms=lower["epistula-timestamp"],
                uuid=lower["epistula-uuid"],
                signed_for=lower["epistula-signed-for"],
                signed_by=lower["epistula-signed-by"],
                signature_hex=lower["epistula-request-signature"],
            )
        except KeyError:
            return None


def _body_hash(body: bytes) -> str:
    return hashlib.sha256(body or b"").hexdigest()


def _signing_message(timestamp_ms: str, uuid: str, signed_for: str, signed_by: str, body: bytes) -> bytes:
    payload = f"{timestamp_ms}.{uuid}.{signed_by}.{signed_for}.{_body_hash(body)}"
    return payload.encode("utf-8")


def sign(
    *,
    keypair: Keypair,
    body: bytes,
    signed_for_ss58: str,
    timestamp_ms: int | None = None,
    uuid: str | None = None,
) -> EpistulaHeaders:
    ts = str(int(timestamp_ms if timestamp_ms is not None else time.time() * 1000))
    nonce = uuid or secrets.token_hex(16)
    msg = _signing_message(ts, nonce, signed_for_ss58, keypair.ss58_address, body)
    sig = "0x" + keypair.sign(msg).hex()
    return EpistulaHeaders(
        version=EPISTULA_VERSION,
        timestamp_ms=ts,
        uuid=nonce,
        signed_for=signed_for_ss58,
        signed_by=keypair.ss58_address,
        signature_hex=sig,
    )


class ReplayCache:
    """Bounded FIFO of seen (sender, uuid) pairs."""

    def __init__(self, max_entries: int = REPLAY_CACHE_MAX) -> None:
        self._max = max(1, int(max_entries))
        self._seen: OrderedDict[tuple[str, str], None] = OrderedDict()

    def remember(self, sender: str, uuid: str) -> bool:
        key = (sender, uuid)
        if key in self._seen:
            self._seen.move_to_end(key)
            return False
        self._seen[key] = None
        while len(self._seen) > self._max:
            self._seen.popitem(last=False)
        return True


@dataclass(frozen=True, slots=True)
class VerifyOutcome:
    ok: bool
    reason: str = ""


def verify(
    *,
    headers: EpistulaHeaders,
    body: bytes,
    receiver_ss58: str,
    replay_cache: ReplayCache,
    now_ms: int | None = None,
    max_skew_ms: int = DEFAULT_TIMESTAMP_SKEW_MS,
) -> VerifyOutcome:
    if headers.version != EPISTULA_VERSION:
        return VerifyOutcome(False, "version")
    if headers.signed_for != receiver_ss58:
        return VerifyOutcome(False, "wrong_receiver")
    try:
        ts_ms = int(headers.timestamp_ms)
    except ValueError:
        return VerifyOutcome(False, "bad_timestamp")
    now = int(now_ms if now_ms is not None else time.time() * 1000)
    if abs(now - ts_ms) > max_skew_ms:
        return VerifyOutcome(False, "stale_timestamp")
    if not replay_cache.remember(headers.signed_by, headers.uuid):
        return VerifyOutcome(False, "replayed_nonce")
    msg = _signing_message(
        headers.timestamp_ms,
        headers.uuid,
        headers.signed_for,
        headers.signed_by,
        body,
    )
    sig_hex = headers.signature_hex.removeprefix("0x")
    try:
        sig = bytes.fromhex(sig_hex)
    except ValueError:
        return VerifyOutcome(False, "bad_signature_hex")
    try:
        peer = Keypair(ss58_address=headers.signed_by)
    except Exception:  # noqa: BLE001
        return VerifyOutcome(False, "bad_sender_ss58")
    if not peer.verify(msg, sig):
        return VerifyOutcome(False, "bad_signature")
    return VerifyOutcome(True)
