"""Perturbed-Mathlib supply: parameterise curated lemma templates with per-epoch constants."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

from lemma.problems.base import Problem


@dataclass(frozen=True, slots=True)
class _Template:
    family: str
    split: str
    imports: tuple[str, ...]
    render: callable  # rng -> (type_expr, theorem_name_hint)


def _name(family: str, seed: int, idx: int) -> str:
    digest = hashlib.sha256(f"{family}/{seed}/{idx}".encode()).hexdigest()[:12]
    return f"perturb_{family}_{digest}"


def _rand_nat(rng: random.Random, lo: int = 2, hi: int = 97) -> int:
    return rng.randint(lo, hi)


def _rand_ident(rng: random.Random) -> str:
    return rng.choice(("lz", "qm", "wf", "kt", "sa", "ub", "rp", "ng", "yh", "ix"))


def _add_comm_nat(rng: random.Random) -> tuple[str, str]:
    a, b = _rand_nat(rng), _rand_nat(rng)
    return f"({a} : Nat) + {b} = {b} + {a}", "add_comm"


def _add_assoc_nat(rng: random.Random) -> tuple[str, str]:
    a, b, c = _rand_nat(rng), _rand_nat(rng), _rand_nat(rng)
    return f"({a} : Nat) + {b} + {c} = {a} + ({b} + {c})", "add_assoc"


def _mul_comm_int(rng: random.Random) -> tuple[str, str]:
    a, b = _rand_nat(rng), _rand_nat(rng)
    return f"({a} : Int) * {b} = {b} * {a}", "mul_comm"


def _nat_le_refl(rng: random.Random) -> tuple[str, str]:
    var = _rand_ident(rng)
    return f"∀ {var} : Nat, {var} ≤ {var}", "le_refl"


def _abs_nonneg_int(rng: random.Random) -> tuple[str, str]:
    var = _rand_ident(rng)
    return f"∀ {var} : Int, |{var}| ≥ 0", "abs_nonneg"


def _sq_nonneg_real(rng: random.Random) -> tuple[str, str]:
    var = _rand_ident(rng)
    return f"∀ {var} : ℝ, {var} ^ 2 ≥ 0", "sq_nonneg"


def _two_mul_eq_add_self(rng: random.Random) -> tuple[str, str]:
    var = _rand_ident(rng)
    return f"∀ {var} : Nat, 2 * {var} = {var} + {var}", "two_mul"


def _pow_zero(rng: random.Random) -> tuple[str, str]:
    var = _rand_ident(rng)
    return f"∀ {var} : Nat, {var} ^ 0 = 1", "pow_zero"


def _list_length_append(rng: random.Random) -> tuple[str, str]:
    a, b = _rand_ident(rng), _rand_ident(rng)
    return (
        f"∀ ({a} {b} : List Nat), ({a} ++ {b}).length = {a}.length + {b}.length",
        "length_append",
    )


def _and_comm(rng: random.Random) -> tuple[str, str]:
    a, b = _rand_ident(rng), _rand_ident(rng)
    return f"∀ {a} {b} : Prop, ({a} ∧ {b}) ↔ ({b} ∧ {a})", "and_comm"


_TEMPLATES: tuple[_Template, ...] = (
    _Template("add_comm_nat", "easy", ("Mathlib",), _add_comm_nat),
    _Template("add_assoc_nat", "easy", ("Mathlib",), _add_assoc_nat),
    _Template("mul_comm_int", "easy", ("Mathlib",), _mul_comm_int),
    _Template("nat_le_refl", "easy", ("Mathlib",), _nat_le_refl),
    _Template("abs_nonneg_int", "medium", ("Mathlib",), _abs_nonneg_int),
    _Template("sq_nonneg_real", "medium", ("Mathlib",), _sq_nonneg_real),
    _Template("two_mul_eq_add_self", "medium", ("Mathlib",), _two_mul_eq_add_self),
    _Template("pow_zero", "easy", ("Mathlib",), _pow_zero),
    _Template("list_length_append", "medium", ("Mathlib",), _list_length_append),
    _Template("and_comm", "easy", ("Mathlib",), _and_comm),
)


class PerturbedMathlibSource:
    name = "perturb_mathlib"

    def __init__(self, lean_toolchain: str, mathlib_rev: str) -> None:
        self._toolchain = lean_toolchain
        self._rev = mathlib_rev

    def draw(self, epoch_id: int, count: int, rng_seed: bytes) -> list[Problem]:
        rng = random.Random(hashlib.sha256(rng_seed + str(epoch_id).encode()).digest())
        out: list[Problem] = []
        for i in range(max(0, int(count))):
            tpl = _TEMPLATES[rng.randrange(len(_TEMPLATES))]
            type_expr, _hint = tpl.render(rng)
            theorem_name = _name(tpl.family, epoch_id, i)
            out.append(
                Problem(
                    id=f"perturb/{epoch_id}/{i}",
                    theorem_name=theorem_name,
                    type_expr=type_expr,
                    split=tpl.split,
                    lean_toolchain=self._toolchain,
                    mathlib_rev=self._rev,
                    imports=tpl.imports,
                    extra={"source": "perturb_mathlib", "family": tpl.family},
                ),
            )
        return out
