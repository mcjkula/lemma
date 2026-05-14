"""Payload size limits for Lemma challenge and response synapses."""

from __future__ import annotations

from lemma.common.config import LemmaSettings
from lemma.protocol import LemmaChallenge
from lemma.protocol_commit_reveal import looks_like_commitment_hex


def synapse_payload_error(
    synapse: LemmaChallenge,
    settings: LemmaSettings,
    *,
    response: bool = True,
) -> str | None:
    cap = settings.lemma_inbound_max_chars
    stmt = synapse.theorem_statement or ""
    if len(stmt) > cap:
        return "theorem_statement too large"
    if not response:
        return None
    phase = (synapse.commit_reveal_phase or "off").strip().lower()
    pc = (synapse.proof_commitment_hex or "").strip()
    if phase == "commit" and pc:
        if not looks_like_commitment_hex(pc):
            return "proof_commitment_hex must be 64 hex chars, with optional 0x prefix"
        if (synapse.proof_script or "").strip():
            return "commit phase response must not include proof_script"
        return None
    pr = synapse.proof_script or ""
    if len(pr) > cap:
        return "proof_script too large"
    return None
