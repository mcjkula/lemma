"""Wire types for validator↔miner over Epistula-signed HTTP."""

from __future__ import annotations

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
