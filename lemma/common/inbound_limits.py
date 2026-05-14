"""Reject oversized HTTP bodies before parsing (renamed from synapse_limits)."""

from __future__ import annotations


def enforce_inbound_max_chars(payload_text: str, *, max_chars: int) -> None:
    """Raise ``ValueError`` when the JSON body would blow past the configured cap."""
    if max_chars <= 0:
        return
    if len(payload_text or "") > int(max_chars):
        raise ValueError(f"inbound payload exceeds LEMMA_INBOUND_MAX_CHARS={max_chars}")
