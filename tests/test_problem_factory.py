"""Problem source factory tests."""

from lemma.common.config import LemmaSettings
from lemma.problems.factory import get_problem_source, resolve_problem
from lemma.problems.hybrid import CuratedCatalogSource, HybridProblemSource


def test_hybrid_default() -> None:
    s = LemmaSettings()
    src = get_problem_source(s)
    assert isinstance(src, HybridProblemSource)


def test_resolve_generated_id() -> None:
    s = LemmaSettings()
    p = resolve_problem(s, "gen/42")
    assert p.id == "gen/42"


def test_resolve_curated_id() -> None:
    curated_id = CuratedCatalogSource().all_problems()[0].id
    s = LemmaSettings()
    p = resolve_problem(s, curated_id)
    assert p.id == curated_id


def test_resolve_unknown_id_rejected() -> None:
    s = LemmaSettings()
    try:
        resolve_problem(s, "mini/demo")
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "Unknown problem id" in str(e)


def test_unknown_source_rejected() -> None:
    s = LemmaSettings(problem_source="frozen")
    try:
        get_problem_source(s)
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "Unknown LEMMA_PROBLEM_SOURCE" in str(e)
