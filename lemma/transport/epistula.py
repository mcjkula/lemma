"""Epistula signed-header transport (sender.receiver.body authenticated)."""

from __future__ import annotations

import hashlib
import secrets
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Final

from bittensor_wallet import Keypair

EPISTULA_VERSION: Final[str] = "2"
DEFAULT_TIMESTAMP_SKEW_MS: Final[int] = 60_000
REPLAY_CACHE_MAX: Final[int] = 4096
_HEADER_KEYS = (
    ("version", "Epistula-Version"),
    ("timestamp_ms", "Epistula-Timestamp"),
    ("uuid", "Epistula-Uuid"),
    ("signed_for", "Epistula-Signed-For"),
    ("signed_by", "Epistula-Signed-By"),
    ("signature_hex", "Epistula-Request-Signature"),
)


@dataclass(frozen=True, slots=True)
class EpistulaHeaders:
    version: str
    timestamp_ms: str
    uuid: str
    signed_for: str
    signed_by: str
    signature_hex: str

    def to_http_headers(self) -> dict[str, str]:
        return {http: getattr(self, attr) for attr, http in _HEADER_KEYS}

    @classmethod
    def from_http_headers(cls, h: dict[str, str]) -> EpistulaHeaders | None:
        lower = {k.lower(): v for k, v in h.items()}
        try:
            return cls(**{attr: lower[http.lower()] for attr, http in _HEADER_KEYS})
        except KeyError:
            return None


@dataclass(frozen=True, slots=True)
class VerifyOutcome:
    ok: bool
    reason: str = ""


def _signing_message(ts: str, uuid: str, signed_for: str, signed_by: str, body: bytes) -> bytes:
    return f"{ts}.{uuid}.{signed_by}.{signed_for}.{hashlib.sha256(body).hexdigest()}".encode()


def sign(
    *, keypair: Keypair, body: bytes, signed_for_ss58: str,
    timestamp_ms: int | None = None, uuid: str | None = None,
) -> EpistulaHeaders:
    ts = str(timestamp_ms if timestamp_ms is not None else int(time.time() * 1000))
    nonce = uuid or secrets.token_hex(16)
    msg = _signing_message(ts, nonce, signed_for_ss58, keypair.ss58_address, body)
    return EpistulaHeaders(
        version=EPISTULA_VERSION, timestamp_ms=ts, uuid=nonce,
        signed_for=signed_for_ss58, signed_by=keypair.ss58_address,
        signature_hex="0x" + keypair.sign(msg).hex(),
    )


class ReplayCache:
    """Bounded FIFO of seen ``(sender, uuid)`` pairs."""

    def __init__(self, max_entries: int = REPLAY_CACHE_MAX) -> None:
        self._max = max(1, max_entries)
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


def verify(
    *, headers: EpistulaHeaders, body: bytes, receiver_ss58: str,
    replay_cache: ReplayCache, now_ms: int | None = None,
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
    now = now_ms if now_ms is not None else int(time.time() * 1000)
    if abs(now - ts_ms) > max_skew_ms:
        return VerifyOutcome(False, "stale_timestamp")
    if not replay_cache.remember(headers.signed_by, headers.uuid):
        return VerifyOutcome(False, "replayed_nonce")
    try:
        sig = bytes.fromhex(headers.signature_hex.removeprefix("0x"))
    except ValueError:
        return VerifyOutcome(False, "bad_signature_hex")
    try:
        peer = Keypair(ss58_address=headers.signed_by)
    except Exception:  # noqa: BLE001
        return VerifyOutcome(False, "bad_sender_ss58")
    msg = _signing_message(headers.timestamp_ms, headers.uuid, headers.signed_for, headers.signed_by, body)
    return VerifyOutcome(True) if peer.verify(msg, sig) else VerifyOutcome(False, "bad_signature")
