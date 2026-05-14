"""Perturbed Mathlib supply produces distinct seeded statements."""

from lemma.supply.perturb_mathlib import PerturbedMathlibSource


def _source() -> PerturbedMathlibSource:
    return PerturbedMathlibSource(lean_toolchain="leanprover/lean4:v4.30.0", mathlib_rev="abc")


def test_draws_requested_count() -> None:
    out = _source().draw(epoch_id=1, count=8, rng_seed=b"seed")
    assert len(out) == 8


def test_distinct_seeds_yield_distinct_statements() -> None:
    a = _source().draw(epoch_id=1, count=4, rng_seed=b"s1")
    b = _source().draw(epoch_id=1, count=4, rng_seed=b"s2")
    assert [p.type_expr for p in a] != [p.type_expr for p in b]


def test_same_seed_is_deterministic() -> None:
    a = _source().draw(epoch_id=7, count=5, rng_seed=b"same")
    b = _source().draw(epoch_id=7, count=5, rng_seed=b"same")
    assert [(p.id, p.type_expr) for p in a] == [(p.id, p.type_expr) for p in b]


def test_problem_carries_source_tag() -> None:
    [p] = _source().draw(epoch_id=2, count=1, rng_seed=b"x")
    assert p.extra.get("source") == "perturb_mathlib"
    assert p.lean_toolchain.startswith("leanprover/")
