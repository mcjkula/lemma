"""Problem catalog primitive (one theorem round)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Solution.lean bridges Challenge ↔ Submission via `exact Submission.<theorem_name>`.
# Different name than `theorem_name` to avoid Lean's duplicate-declaration error.
SOLUTION_BRIDGE_THEOREM = "LemmaSubmissionBridge"


@dataclass(frozen=True)
class Problem:
    id: str
    theorem_name: str
    type_expr: str
    split: str
    lean_toolchain: str
    mathlib_rev: str
    imports: tuple[str, ...] = ("Mathlib",)
    extra: dict[str, Any] = field(default_factory=dict)

    def _imports_block(self) -> str:
        return "\n".join(f"import {m}" for m in self.imports)

    def challenge_source(self) -> str:
        cf = self.extra.get("challenge_full")
        if isinstance(cf, str) and cf.strip():
            return f"{self._imports_block()}\n\n{cf.strip()}\n" if self.imports else cf.strip() + "\n"
        return f"{self._imports_block()}\n\ntheorem {self.theorem_name} : {self.type_expr} := by\n  sorry\n"

    def solution_source(self) -> str:
        sf = self.extra.get("solution_full")
        if isinstance(sf, str) and sf.strip():
            return sf.strip() + "\n"
        return (
            f"{self._imports_block()}\nimport Submission\n\n"
            f"theorem {SOLUTION_BRIDGE_THEOREM} : {self.type_expr} := by\n"
            f"  exact Submission.{self.theorem_name}\n"
        )
