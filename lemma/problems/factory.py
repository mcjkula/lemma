"""Construct the active ProblemSource from settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lemma.problems.base import Problem, ProblemSource
from lemma.problems.generated import GeneratedProblemSource
from lemma.problems.hybrid import CuratedCatalogSource, HybridProblemSource

if TYPE_CHECKING:
    from lemma.common.config import LemmaSettings


def get_problem_source(settings: LemmaSettings) -> ProblemSource:
    mode = (settings.problem_source or "hybrid").strip().lower()
    if mode == "hybrid":
        return HybridProblemSource(
            generated=GeneratedProblemSource(legacy_plain_rng=settings.lemma_generated_legacy_plain_rng),
            generated_weight=settings.lemma_hybrid_generated_weight,
            catalog_weight=settings.lemma_hybrid_catalog_weight,
        )
    if mode != "generated":
        raise ValueError(f"Unknown LEMMA_PROBLEM_SOURCE={settings.problem_source!r}")
    return GeneratedProblemSource(legacy_plain_rng=settings.lemma_generated_legacy_plain_rng)


def resolve_problem(settings: LemmaSettings, problem_id: str) -> Problem:
    if problem_id.startswith("gen/"):
        return GeneratedProblemSource(
            legacy_plain_rng=settings.lemma_generated_legacy_plain_rng,
        ).get(problem_id)
    if problem_id.startswith("curated/"):
        return CuratedCatalogSource().get(problem_id)
    raise ValueError(f"Unknown problem id {problem_id!r}; use gen/<seed> or curated/<id>")
