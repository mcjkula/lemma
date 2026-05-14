"""Wire types for validator↔miner over Epistula-signed HTTP."""

from __future__ import annotations

from typing import ClassVar

import bittensor as bt
from pydantic import BaseModel, Field


class ChallengePayload(BaseModel):
    """Validator → miner challenge envelope (POST /lemma/commit, /lemma/reveal)."""

    theorem_id: str
    theorem_statement: str
    imports: list[str] = Field(default_factory=lambda: ["Mathlib"])
    lean_toolchain: str
    mathlib_rev: str
    deadline_block: int
    metronome_id: str
    phase: str = "off"


class CommitPayload(BaseModel):
    """Miner reply for the commit phase."""

    theorem_id: str
    metronome_id: str
    proof_commitment_hex: str


class RevealPayload(BaseModel):
    """Miner reply for the reveal phase (or single-phase response)."""

    theorem_id: str
    metronome_id: str
    proof_script: str
    commit_reveal_nonce_hex: str | None = None
    model_card: str | None = None


class VerifyReply(BaseModel):
    accepted: bool
    reason: str = ""


# Legacy synapse-shaped envelope used by remaining bt.Axon / bt.Dendrite paths
# until Stage 1 cutover completes; treat as deprecated.
class LemmaChallenge(bt.Synapse):
    required_hash_fields: ClassVar[tuple[str, ...]] = (
        "theorem_id",
        "metronome_id",
        "theorem_statement",
        "lean_toolchain",
        "mathlib_rev",
        "deadline_block",
        "proof_script",
    )

    theorem_id: str
    theorem_statement: str
    imports: list[str] = Field(default_factory=lambda: ["Mathlib"])
    lean_toolchain: str
    mathlib_rev: str
    deadline_unix: int
    deadline_block: int | None = None
    metronome_id: str

    proof_script: str | None = None
    model_card: str | None = None
    commit_reveal_phase: str = "off"
    proof_commitment_hex: str | None = None
    commit_reveal_nonce_hex: str | None = None

    def deserialize(self) -> LemmaChallenge:
        return self


def synapse_miner_response_integrity_ok(s: LemmaChallenge) -> bool:
    expected = (s.computed_body_hash or "").strip()
    if s.deadline_block is None:
        return False
    return not expected or s.body_hash == expected
