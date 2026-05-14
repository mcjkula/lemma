"""One scoring round: broadcast K theorems, rank first-to-solve, set weights."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

import bittensor
import httpx
from loguru import logger

from lemma.catalog.constants import DEFAULT_LEAN_TOOLCHAIN, DEFAULT_MATHLIB_REV
from lemma.common.problem_seed import (
    effective_chain_head_for_problem_seed,
    resolve_problem_seed,
)
from lemma.common.subtensor import get_subtensor
from lemma.lean.sandbox import VerifyResult
from lemma.lean.verify_runner import run_lean_verify
from lemma.problems.base import Problem
from lemma.protocol import ChallengePayload, RevealPayload
from lemma.scoring.champion_decay import apply_decay
from lemma.scoring.dedup import submission_fingerprint
from lemma.scoring.first_to_solve import Solve, rank_solvers
from lemma.scoring.observed_difficulty import base_reward, solve_fractions
from lemma.scoring.pareto_subset import layer_weights, pareto_layers
from lemma.scoring.reputation import load_reputation, save_reputation
from lemma.supply.base import Source
from lemma.supply.competition_formal import CompetitionFormalSource
from lemma.supply.mathlib_sorrys import MathlibSorrysSource
from lemma.supply.perturb_mathlib import PerturbedMathlibSource
from lemma.supply.pipeline import build_batch, commit_batch
from lemma.transport.client import signed_post
from lemma.validator.corpus import CorpusEntry, append as append_corpus
from lemma.validator.weights_policy import build_full_weights

if TYPE_CHECKING:
    from lemma.common.config import LemmaSettings


_VERIFY_INFRA_REASONS = frozenset({"timeout", "oom", "docker_error", "remote_error"})
_RANK_DECAY: float = 0.5
_MAX_RANK_PAID: int = 10


def _verify_result_is_infra_failure(vr: VerifyResult) -> bool:
    return not vr.passed and vr.reason in _VERIFY_INFRA_REASONS


def _miner_url(metagraph: bittensor.metagraph, uid: int) -> str | None:
    try:
        ax = metagraph.axons[uid]
    except (IndexError, AttributeError):
        return None
    ip = (getattr(ax, "ip", "") or "").strip()
    port = int(getattr(ax, "port", 0) or 0)
    if not ip or ip == "0.0.0.0" or port <= 0:
        return None
    return f"http://{ip}:{port}"


def _registration_blocks(metagraph: bittensor.metagraph) -> dict[int, int]:
    out: dict[int, int] = {}
    blocks = getattr(metagraph, "block_at_registration", None)
    if blocks is None:
        return out
    for uid in range(metagraph.n):
        try:
            out[uid] = int(blocks[uid])
        except (IndexError, TypeError, ValueError):
            continue
    return out


async def _query_one(
    *,
    client: httpx.AsyncClient,
    url: str,
    keypair: bittensor.Keypair,
    receiver_ss58: str,
    body: bytes,
    timeout_s: float,
) -> RevealPayload | None:
    try:
        r = await signed_post(
            client,
            f"{url}/lemma/reveal",
            body,
            keypair=keypair,
            signed_for_ss58=receiver_ss58,
            timeout_s=timeout_s,
        )
    except httpx.HTTPError as e:
        logger.debug("miner http error: {}", e)
        return None
    if r.status_code != 200:
        return None
    try:
        return RevealPayload.model_validate_json(r.content)
    except (ValueError, TypeError):
        return None


async def _broadcast_theorem(
    *,
    client: httpx.AsyncClient,
    settings: LemmaSettings,
    wallet: bittensor.Wallet,
    metagraph: bittensor.metagraph,
    challenge: ChallengePayload,
    timeout_s: float,
) -> dict[int, RevealPayload]:
    body = challenge.model_dump_json().encode("utf-8")
    sem = asyncio.Semaphore(max(1, settings.lemma_lean_verify_max_concurrent * 2))

    async def _one(uid: int) -> tuple[int, RevealPayload | None]:
        url = _miner_url(metagraph, uid)
        if url is None:
            return uid, None
        receiver_ss58 = metagraph.hotkeys[uid]
        async with sem:
            reply = await _query_one(
                client=client,
                url=url,
                keypair=wallet.hotkey,
                receiver_ss58=receiver_ss58,
                body=body,
                timeout_s=timeout_s,
            )
        return uid, reply

    results = await asyncio.gather(*(_one(uid) for uid in range(metagraph.n)))
    out: dict[int, RevealPayload] = {}
    for uid, reply in results:
        if reply is not None and reply.proof_script:
            out[uid] = reply
    return out


def _verify_proof(settings: LemmaSettings, problem: Problem, proof_script: str) -> VerifyResult:
    try:
        return run_lean_verify(
            settings,
            verify_timeout_s=settings.lean_verify_timeout_s,
            problem=problem,
            proof_script=proof_script,
        )
    except Exception as e:  # noqa: BLE001
        return VerifyResult(passed=False, reason="docker_error", stderr_tail=str(e)[:8000])


def _build_streams(settings: LemmaSettings) -> dict[str, Source]:
    streams: dict[str, Source] = {
        "P": PerturbedMathlibSource(
            lean_toolchain=DEFAULT_LEAN_TOOLCHAIN,
            mathlib_rev=DEFAULT_MATHLIB_REV,
        ),
    }
    if settings.lemma_mathlib_root_path is not None:
        streams["M"] = MathlibSorrysSource(
            settings.lemma_mathlib_root_path,
            lean_toolchain=DEFAULT_LEAN_TOOLCHAIN,
            mathlib_rev=DEFAULT_MATHLIB_REV,
        )
    if settings.lemma_competition_formal_path is not None:
        streams["C"] = CompetitionFormalSource(
            settings.lemma_competition_formal_path,
            lean_toolchain=DEFAULT_LEAN_TOOLCHAIN,
            mathlib_rev=DEFAULT_MATHLIB_REV,
        )
    return streams


def _supply_pipeline_problems(
    settings: LemmaSettings,
    *,
    epoch_id: int,
    target_count: int,
    subtensor: object,
    wallet: object,
) -> list[Problem]:
    batch = build_batch(
        settings,
        _build_streams(settings),
        epoch_id=epoch_id,
        target_count=target_count,
        freshness_path=settings.lemma_supply_freshness_path,
        skip_baseline_filter=True,
    )
    commit_batch(batch, subtensor, wallet=wallet, netuid=settings.netuid)
    return batch.problems


def _verified_solves(
    settings: LemmaSettings,
    problems: dict[str, Problem],
    replies_by_theorem: dict[str, dict[int, RevealPayload]],
) -> tuple[dict[str, set[int]], dict[str, dict[int, str]]]:
    solved: dict[str, set[int]] = {tid: set() for tid in problems}
    proofs: dict[str, dict[int, str]] = {tid: {} for tid in problems}
    seen_fingerprints: dict[str, set[str]] = {tid: set() for tid in problems}
    for tid, replies in replies_by_theorem.items():
        problem = problems[tid]
        for uid, reply in replies.items():
            fp = submission_fingerprint(problem.challenge_source(), reply.proof_script)
            if fp in seen_fingerprints[tid]:
                continue
            vr = _verify_proof(settings, problem, reply.proof_script)
            if _verify_result_is_infra_failure(vr):
                continue
            if not vr.passed:
                continue
            seen_fingerprints[tid].add(fp)
            solved[tid].add(uid)
            proofs[tid][uid] = reply.proof_script
    return solved, proofs


def _compose_weights(
    solved_by_theorem: dict[str, set[int]],
    active_uids: set[int],
    registration_block: dict[int, int],
    commit_block: int,
    reign_by_uid: dict[int, int],
) -> dict[int, float]:
    fractions = solve_fractions(solved_by_theorem, active_uids)
    solves = [
        Solve(miner_uid=uid, theorem_id=tid, commit_block=commit_block)
        for tid, uids in solved_by_theorem.items()
        for uid in uids
    ]
    ranks = rank_solvers(solves, registration_block)
    rewards: dict[int, dict[str, float]] = {}
    for tid, uids in solved_by_theorem.items():
        r0 = base_reward(fractions.get(tid, 0.0))
        if r0 <= 0.0:
            continue
        for uid in uids:
            rank = ranks.get((tid, uid), _MAX_RANK_PAID)
            if rank >= _MAX_RANK_PAID:
                continue
            rewards.setdefault(uid, {})[tid] = r0 * (_RANK_DECAY**rank)
    if not rewards:
        return {}
    layers = pareto_layers(rewards)
    weights = layer_weights(layers)
    return apply_decay(weights, reign_by_uid)


def _update_reigns(reign_by_uid: dict[int, int], champions: list[int]) -> dict[int, int]:
    fresh: dict[int, int] = {}
    for uid in champions:
        fresh[uid] = int(reign_by_uid.get(uid, 0)) + 1
    return fresh


async def run_epoch(settings: LemmaSettings, *, dry_run: bool = False) -> dict[int, float]:
    t0 = time.perf_counter()
    wallet = bittensor.Wallet(name=settings.wallet_cold, hotkey=settings.wallet_hot)
    subtensor = get_subtensor(settings)
    metagraph = subtensor.metagraph(settings.netuid)
    cur_block = int(subtensor.get_current_block())
    seed_head = effective_chain_head_for_problem_seed(
        cur_block, int(settings.lemma_problem_seed_chain_head_slack_blocks or 0),
    )
    problem_seed, _seed_tag = resolve_problem_seed(
        chain_head_block=seed_head,
        netuid=settings.netuid,
        mode=settings.problem_seed_mode,
        quantize_blocks=settings.problem_seed_quantize_blocks,
        subtensor=subtensor,
    )
    k = max(1, int(settings.lemma_epoch_problem_count))
    problems_list = _supply_pipeline_problems(
        settings,
        epoch_id=problem_seed,
        target_count=k,
        subtensor=subtensor,
        wallet=wallet,
    )
    if not problems_list:
        logger.warning("supply pipeline returned no problems epoch={}", problem_seed)
        return {}
    problems = {p.id: p for p in problems_list}

    replies_by_theorem: dict[str, dict[int, RevealPayload]] = {}
    async with httpx.AsyncClient() as client:
        for problem in problems_list:
            challenge = ChallengePayload(
                theorem_id=problem.id,
                theorem_statement=problem.challenge_source(),
                imports=list(problem.imports),
                lean_toolchain=problem.lean_toolchain,
                mathlib_rev=problem.mathlib_rev,
                deadline_block=cur_block + 1,
                metronome_id=str(problem_seed),
            )
            replies_by_theorem[problem.id] = await _broadcast_theorem(
                client=client,
                settings=settings,
                wallet=wallet,
                metagraph=metagraph,
                challenge=challenge,
                timeout_s=float(settings.forward_wait_max_s),
            )

    solved, proofs = _verified_solves(settings, problems, replies_by_theorem)

    rep_store = load_reputation(settings.lemma_reputation_state_path)
    weights = _compose_weights(
        solved_by_theorem=solved,
        active_uids=set(range(metagraph.n)),
        registration_block=_registration_blocks(metagraph),
        commit_block=cur_block,
        reign_by_uid=rep_store.reign_by_uid,
    )
    champions = [uid for uid, w in weights.items() if w > 0.0]
    rep_store.reign_by_uid = _update_reigns(rep_store.reign_by_uid, champions)
    if not dry_run:
        save_reputation(settings.lemma_reputation_state_path, rep_store)

    full, skip = build_full_weights(metagraph.n, weights)
    if not skip and not dry_run:
        subtensor.set_weights(
            wallet=wallet,
            netuid=settings.netuid,
            uids=list(range(metagraph.n)),
            weights=full,
            wait_for_inclusion=False,
        )

    if not dry_run:
        corpus_entries = [
            CorpusEntry(
                epoch_id=problem_seed,
                theorem_id=tid,
                theorem_statement=problems[tid].challenge_source(),
                proof_script=proof,
                miner_hotkey_ss58=metagraph.hotkeys[uid],
                commit_block=cur_block,
                mathlib_rev=problems[tid].mathlib_rev,
                lean_toolchain=problems[tid].lean_toolchain,
            )
            for tid, by_uid in proofs.items()
            for uid, proof in by_uid.items()
        ]
        append_corpus(corpus_entries)

    logger.info(
        "epoch theorems={} solved={} weights={} skip={} elapsed={:.2f}s",
        len(problems),
        sum(len(v) for v in solved.values()),
        len(weights),
        skip,
        time.perf_counter() - t0,
    )
    return weights
