"""Wire types for validator ↔ miner over Epistula-signed HTTP."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, TypeVar


@dataclass(frozen=True, slots=True)
class ChallengePayload:
    theorem_id: str
    theorem_statement: str
    lean_toolchain: str
    mathlib_rev: str
    deadline_block: int
    metronome_id: str
    imports: list[str] = field(default_factory=lambda: ["Mathlib"])


@dataclass(frozen=True, slots=True)
class RevealPayload:
    theorem_id: str
    metronome_id: str
    proof_script: str


@dataclass(frozen=True, slots=True)
class VerifyReply:
    accepted: bool
    reason: str = ""


def to_json(obj: Any) -> bytes:
    return json.dumps(asdict(obj), separators=(",", ":")).encode("utf-8")


_T = TypeVar("_T")


def from_json(cls: type[_T], body: bytes | str) -> _T:
    raw = body.decode("utf-8") if isinstance(body, bytes) else body
    return cls(**json.loads(raw))
