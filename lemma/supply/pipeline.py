"""Per-epoch supply: streams P/M/C → filter → freshness → chain anchor."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import bittensor

from lemma.lean import DEFAULT_LEAN_TOOLCHAIN, DEFAULT_MATHLIB_REV
from lemma.problems.base import Problem
from lemma.supply.base import Source
from lemma.supply.baseline_filter import is_trivial
from lemma.supply.competition_formal import CompetitionFormalSource
from lemma.supply.freshness import FreshnessRegistry, statement_hash
from lemma.supply.mathlib_sorrys import MathlibSorrysSource
from lemma.supply.perturb_mathlib import PerturbedMathlibSource
from lemma.supply.registry import EpochCommitment, merkle_root
from lemma.transport.chain_commit import anchor_batch

if TYPE_CHECKING:
    from lemma.common.config import LemmaSettings


_DEFAULT_RATIOS: tuple[tuple[str, float], ...] = (("P", 0.60), ("M", 0.25), ("C", 0.15))


@dataclass(frozen=True, slots=True)
class SupplyBatch:
    epoch_id: int
    problems: list[Problem]
    commitment: EpochCommitment


def _draw_from_streams(
    streams: dict[str, Source], epoch_id: int, count: int,
    ratios: tuple[tuple[str, float], ...],
) -> list[Problem]:
    out: list[Problem] = []
    for key, ratio in ratios:
        source = streams.get(key)
        n = max(0, round(count * ratio))
        if source is None or n <= 0:
            continue
        seed = hashlib.sha256(f"{epoch_id}:{key}".encode()).digest()
        out.extend(source.draw(epoch_id, n, seed))
    return out


def build_batch(
    settings: LemmaSettings,
    streams: dict[str, Source],
    *,
    epoch_id: int,
    target_count: int,
    freshness_path: Path | None = None,
    ratios: tuple[tuple[str, float], ...] = _DEFAULT_RATIOS,
    skip_baseline_filter: bool = False,
) -> SupplyBatch:
    candidates = _draw_from_streams(streams, epoch_id, max(1, target_count * 2), ratios)
    registry = FreshnessRegistry(freshness_path, settings.lemma_supply_public_corpus_bloom_path)
    accepted: list[Problem] = []
    hashes: list[str] = []
    for problem in candidates:
        if len(accepted) >= target_count:
            break
        statement = problem.challenge_source()
        if not registry.is_fresh(statement):
            continue
        if not skip_baseline_filter and is_trivial(settings, problem):
            continue
        registry.record(statement)
        accepted.append(problem)
        hashes.append(statement_hash(statement))
    return SupplyBatch(
        epoch_id=epoch_id,
        problems=accepted,
        commitment=EpochCommitment(epoch_id=epoch_id, root_hex=merkle_root(hashes)),
    )


def build_streams(settings: LemmaSettings) -> dict[str, Source]:
    streams: dict[str, Source] = {
        "P": PerturbedMathlibSource(lean_toolchain=DEFAULT_LEAN_TOOLCHAIN, mathlib_rev=DEFAULT_MATHLIB_REV),
    }
    if settings.lemma_mathlib_root_path is not None:
        streams["M"] = MathlibSorrysSource(
            settings.lemma_mathlib_root_path,
            lean_toolchain=DEFAULT_LEAN_TOOLCHAIN, mathlib_rev=DEFAULT_MATHLIB_REV,
        )
    if settings.lemma_competition_formal_path is not None:
        streams["C"] = CompetitionFormalSource(
            settings.lemma_competition_formal_path,
            lean_toolchain=DEFAULT_LEAN_TOOLCHAIN, mathlib_rev=DEFAULT_MATHLIB_REV,
        )
    return streams


def build_problems_for_epoch(
    settings: LemmaSettings,
    *,
    epoch_id: int,
    target_count: int,
    subtensor: bittensor.Subtensor | None,
    wallet: bittensor.Wallet,
) -> tuple[list[Problem], int]:
    batch = build_batch(
        settings, build_streams(settings),
        epoch_id=epoch_id, target_count=target_count,
        freshness_path=settings.lemma_supply_freshness_path, skip_baseline_filter=True,
    )
    anchored_block = anchor_batch(
        subtensor, wallet=wallet, netuid=settings.netuid,
        epoch_id=epoch_id, merkle_root_hex=batch.commitment.root_hex,
    )
    return batch.problems, anchored_block
