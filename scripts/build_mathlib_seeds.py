#!/usr/bin/env python3
"""Generate ``data/mathlib_seeds.jsonl`` — the Stream P seed corpus.

Each line is one seed:

    {"id": "<stable-id>", "family": "<lemma-family>", "split": "easy|medium|hard",
     "type_expr": "<Lean expression with {param} placeholders>",
     "imports": ["Mathlib", ...],
     "params": {"<name>": {"kind": "nat|int|ident", "lo": int, "hi": int}}}

``perturb_mathlib.PerturbedMathlibSource`` samples params via a per-epoch RNG
at draw time and renders ``type_expr``.
"""

from __future__ import annotations

import json
from pathlib import Path

_IDENT_POOL = ("lz", "qm", "wf", "kt", "sa", "ub", "rp", "ng", "yh", "ix", "av", "br", "co", "dn")
_OUT = Path(__file__).resolve().parent.parent / "data" / "mathlib_seeds.jsonl"


def _nat_p(lo: int = 2, hi: int = 97) -> dict[str, object]:
    return {"kind": "nat", "lo": lo, "hi": hi}


def _int_p(lo: int = -50, hi: int = 97) -> dict[str, object]:
    return {"kind": "int", "lo": lo, "hi": hi}


def _ident_p() -> dict[str, object]:
    return {"kind": "ident", "pool": list(_IDENT_POOL)}


def _seed(seed_id: str, family: str, split: str, type_expr: str, params: dict[str, object]) -> dict[str, object]:
    return {
        "id": seed_id, "family": family, "split": split,
        "type_expr": type_expr, "imports": ["Mathlib"], "params": params,
    }


def _commutativity() -> list[dict[str, object]]:
    out = []
    cases = [("Nat", "add", "+", "easy"), ("Nat", "mul", "*", "easy"),
             ("Int", "add", "+", "easy"), ("Int", "mul", "*", "easy"),
             ("ℝ", "add", "+", "medium"), ("ℝ", "mul", "*", "medium"),
             ("ℚ", "add", "+", "medium"), ("ℚ", "mul", "*", "medium")]
    windows = [(2, 50), (51, 199), (200, 999), (1000, 9999)]
    for typ, op_name, op, split in cases:
        for lo, hi in windows:
            params = _int_p(-hi, hi) if typ == "Int" else _nat_p(lo, hi)
            out.append(_seed(
                f"{op_name}_comm_{typ.lower()}_{lo}_{hi}", f"{op_name}_comm", split,
                f"({{a}} : {typ}) {op} {{b}} = {{b}} {op} {{a}}",
                {"a": params, "b": params},
            ))
    return out


def _associativity() -> list[dict[str, object]]:
    out = []
    cases = [("Nat", "add", "+", "easy"), ("Nat", "mul", "*", "medium"),
             ("Int", "add", "+", "easy"), ("Int", "mul", "*", "medium"),
             ("ℝ", "add", "+", "medium"), ("ℝ", "mul", "*", "medium")]
    windows = [(2, 50), (51, 199), (200, 999), (1000, 9999)]
    for typ, op_name, op, split in cases:
        for lo, hi in windows:
            params = _int_p(-hi, hi) if typ == "Int" else _nat_p(lo, hi)
            out.append(_seed(
                f"{op_name}_assoc_{typ.lower()}_{lo}_{hi}", f"{op_name}_assoc", split,
                f"(({{a}} : {typ}) {op} {{b}}) {op} {{c}} = {{a}} {op} ({{b}} {op} {{c}})",
                {"a": params, "b": params, "c": params},
            ))
    return out


def _identity_elements() -> list[dict[str, object]]:
    out = []
    cases = [
        ("Nat", "add", "+", "0", "add_zero", "easy"),
        ("Nat", "add", "+", "0", "zero_add", "easy"),
        ("Nat", "mul", "*", "1", "mul_one", "easy"),
        ("Nat", "mul", "*", "1", "one_mul", "easy"),
        ("Nat", "mul", "*", "0", "mul_zero", "easy"),
        ("Int", "add", "+", "0", "add_zero", "easy"),
        ("Int", "mul", "*", "1", "mul_one", "easy"),
        ("Int", "mul", "*", "0", "mul_zero", "easy"),
        ("ℝ", "add", "+", "0", "add_zero", "medium"),
        ("ℝ", "mul", "*", "1", "mul_one", "medium"),
        ("ℚ", "add", "+", "0", "add_zero", "medium"),
    ]
    windows = [(2, 50), (51, 199), (200, 999), (1000, 9999), (10_000, 999_999)]
    for typ, _op_name, op, ident, fam, split in cases:
        for lo, hi in windows:
            params = _int_p(-hi, hi) if typ == "Int" else _nat_p(lo, hi)
            if fam.startswith("zero_") or fam.startswith("one_"):
                expr = f"({ident} : {typ}) {op} {{a}} = {{a}}"
            else:
                expr = f"({{a}} : {typ}) {op} {ident} = {{a}}"
            out.append(_seed(f"{fam}_{typ.lower()}_{lo}_{hi}", fam, split, expr, {"a": params}))
    return out


def _absolute_values_and_squares() -> list[dict[str, object]]:
    out = []
    for typ, split in [("Int", "medium"), ("ℝ", "medium"), ("ℚ", "medium")]:
        for _ in range(8):
            out.append(_seed(
                f"abs_nonneg_{typ.lower()}_v{_}", "abs_nonneg", split,
                f"∀ {{x}} : {typ}, |{{x}}| ≥ 0", {"x": _ident_p()},
            ))
            out.append(_seed(
                f"sq_nonneg_{typ.lower()}_v{_}", "sq_nonneg", split,
                f"∀ {{x}} : {typ}, {{x}} ^ 2 ≥ 0", {"x": _ident_p()},
            ))
    return out


def _powers() -> list[dict[str, object]]:
    out = []
    for typ, split in [("Nat", "easy"), ("Int", "medium"), ("ℝ", "medium"), ("ℚ", "medium")]:
        for v in range(6):
            out.append(_seed(f"pow_zero_{typ.lower()}_v{v}", "pow_zero", split,
                             f"∀ {{x}} : {typ}, {{x}} ^ 0 = 1", {"x": _ident_p()}))
            out.append(_seed(f"pow_one_{typ.lower()}_v{v}", "pow_one", split,
                             f"∀ {{x}} : {typ}, {{x}} ^ 1 = {{x}}", {"x": _ident_p()}))
    return out


def _order_axioms() -> list[dict[str, object]]:
    out = []
    for typ, split in [("Nat", "easy"), ("Int", "easy"), ("ℝ", "medium"), ("ℚ", "medium")]:
        for v in range(6):
            out.append(_seed(f"le_refl_{typ.lower()}_v{v}", "le_refl", split,
                             f"∀ {{x}} : {typ}, {{x}} ≤ {{x}}", {"x": _ident_p()}))
            out.append(_seed(f"lt_irrefl_{typ.lower()}_v{v}", "lt_irrefl", split,
                             f"∀ {{x}} : {typ}, ¬ ({{x}} < {{x}})", {"x": _ident_p()}))
    return out


def _list_and_finset() -> list[dict[str, object]]:
    out = []
    for v in range(10):
        out.append(_seed(f"length_append_v{v}", "length_append", "medium",
                         "∀ ({a} {b} : List Nat), ({a} ++ {b}).length = {a}.length + {b}.length",
                         {"a": _ident_p(), "b": _ident_p()}))
        out.append(_seed(f"length_nil_v{v}", "length_nil", "easy",
                         "([] : List Nat).length = 0", {}))
        out.append(_seed(f"reverse_reverse_v{v}", "reverse_reverse", "medium",
                         "∀ ({a} : List Nat), {a}.reverse.reverse = {a}", {"a": _ident_p()}))
        out.append(_seed(f"append_nil_v{v}", "append_nil", "easy",
                         "∀ ({a} : List Nat), {a} ++ [] = {a}", {"a": _ident_p()}))
        out.append(_seed(f"nil_append_v{v}", "nil_append", "easy",
                         "∀ ({a} : List Nat), [] ++ {a} = {a}", {"a": _ident_p()}))
    return out


def _propositional_logic() -> list[dict[str, object]]:
    out = []
    families = [
        ("and_comm", "({a} ∧ {b}) ↔ ({b} ∧ {a})"),
        ("or_comm", "({a} ∨ {b}) ↔ ({b} ∨ {a})"),
        ("and_assoc", "(({a} ∧ {b}) ∧ {c}) ↔ ({a} ∧ ({b} ∧ {c}))"),
        ("or_assoc", "(({a} ∨ {b}) ∨ {c}) ↔ ({a} ∨ ({b} ∨ {c}))"),
        ("not_not_iff", "¬ ¬ {a} ↔ {a}"),
        ("and_self", "({a} ∧ {a}) ↔ {a}"),
        ("or_self", "({a} ∨ {a}) ↔ {a}"),
        ("iff_self", "({a} ↔ {a})"),
    ]
    for fam, expr_tail in families:
        for v in range(6):
            forall = "∀ {a} {b} {c} : Prop, " if "{c}" in expr_tail else (
                "∀ {a} {b} : Prop, " if "{b}" in expr_tail else "∀ {a} : Prop, ")
            params = {"a": _ident_p()}
            if "{b}" in expr_tail:
                params["b"] = _ident_p()
            if "{c}" in expr_tail:
                params["c"] = _ident_p()
            out.append(_seed(f"{fam}_v{v}", fam, "easy", forall + expr_tail, params))
    return out


def _arithmetic_identities() -> list[dict[str, object]]:
    out = []
    families = [
        ("two_mul", "∀ {x} : Nat, 2 * {x} = {x} + {x}"),
        ("succ_pred_eq", "∀ {x} : Nat, {x} + 1 - 1 = {x}"),
        ("nat_zero_lt_succ", "∀ {x} : Nat, 0 < {x} + 1"),
        ("neg_neg", "∀ {x} : Int, - - {x} = {x}"),
        ("sub_self", "∀ {x} : Int, {x} - {x} = 0"),
        ("neg_zero", "(- 0 : Int) = 0"),
        ("add_neg_self", "∀ {x} : Int, {x} + (- {x}) = 0"),
    ]
    for fam, expr in families:
        for v in range(8):
            params = {"x": _ident_p()} if "{x}" in expr else {}
            split = "easy" if "Int" not in expr else "medium"
            out.append(_seed(f"{fam}_v{v}", fam, split, expr, params))
    return out


def _modular_arithmetic() -> list[dict[str, object]]:
    out = []
    families = [
        ("nat_mod_self", "∀ {x} : Nat, {x} % {x} = 0"),
        ("nat_mod_one", "∀ {x} : Nat, {x} % 1 = 0"),
        ("nat_div_one", "∀ {x} : Nat, {x} / 1 = {x}"),
        ("nat_mul_mod_left", "∀ {x} : Nat, ({x} * {x}) % {x} = 0"),
    ]
    for fam, expr in families:
        for v in range(8):
            out.append(_seed(f"{fam}_v{v}", fam, "medium", expr, {"x": _ident_p()}))
    return out


def _min_max() -> list[dict[str, object]]:
    out = []
    families = [
        ("min_self", "∀ {x} : Nat, min {x} {x} = {x}"),
        ("max_self", "∀ {x} : Nat, max {x} {x} = {x}"),
        ("min_comm_nat", "∀ {x} {y} : Nat, min {x} {y} = min {y} {x}"),
        ("max_comm_nat", "∀ {x} {y} : Nat, max {x} {y} = max {y} {x}"),
        ("min_le_left", "∀ {x} {y} : Nat, min {x} {y} ≤ {x}"),
        ("max_le_max_right", "∀ {x} : Nat, {x} ≤ max {x} {x}"),
    ]
    for fam, expr in families:
        for v in range(6):
            params: dict[str, object] = {"x": _ident_p()}
            if "{y}" in expr:
                params["y"] = _ident_p()
            out.append(_seed(f"{fam}_v{v}", fam, "easy", expr, params))
    return out


def _concrete_arithmetic() -> list[dict[str, object]]:
    out = []
    for a in range(1, 21):
        for b in range(1, 21):
            out.append(_seed(
                f"concrete_add_comm_{a}_{b}", "concrete_add_comm", "easy",
                f"({a} : Nat) + {b} = {b} + {a}", {},
            ))
    return out


def build_all() -> list[dict[str, object]]:
    seeds: list[dict[str, object]] = []
    seeds.extend(_commutativity())
    seeds.extend(_associativity())
    seeds.extend(_identity_elements())
    seeds.extend(_absolute_values_and_squares())
    seeds.extend(_powers())
    seeds.extend(_order_axioms())
    seeds.extend(_list_and_finset())
    seeds.extend(_propositional_logic())
    seeds.extend(_arithmetic_identities())
    seeds.extend(_modular_arithmetic())
    seeds.extend(_min_max())
    seeds.extend(_concrete_arithmetic())
    return seeds


def main() -> int:
    seeds = build_all()
    seen: set[str] = set()
    deduped: list[dict[str, object]] = []
    for s in seeds:
        sid = str(s["id"])
        if sid in seen:
            continue
        seen.add(sid)
        deduped.append(s)
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    with _OUT.open("w", encoding="utf-8") as f:
        for s in deduped:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"wrote {len(deduped)} seeds to {_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
