"""Wire types for validator ↔ miner over Epistula-signed HTTP."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ChallengePayload:
    theorem_id: str
    theorem_statement: str
    lean_toolchain: str
    mathlib_rev: str
    deadline_block: int
    metronome_id: str
    imports: list[str] = field(default_factory=lambda: ["Mathlib"])
    phase: str = "off"


@dataclass(frozen=True, slots=True)
class CommitPayload:
    theorem_id: str
    metronome_id: str
    proof_commitment_hex: str


@dataclass(frozen=True, slots=True)
class RevealPayload:
    theorem_id: str
    metronome_id: str
    proof_script: str
    commit_reveal_nonce_hex: str | None = None
    model_card: str | None = None


@dataclass(frozen=True, slots=True)
class VerifyReply:
    accepted: bool
    reason: str = ""


def to_json(obj: Any) -> bytes:
    return json.dumps(asdict(obj), separators=(",", ":")).encode("utf-8")


def from_json(cls: type, body: bytes | str) -> Any:
    raw = body.decode("utf-8") if isinstance(body, bytes) else body
    return cls(**json.loads(raw))
