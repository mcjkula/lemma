"""One scoring round over Epistula-signed HTTP."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

import bittensor as bt
import httpx
from loguru import logger

from lemma.common.block_deadline import compute_forward_deadline_and_wait
from lemma.common.problem_seed import (
    effective_chain_head_for_problem_seed,
    resolve_problem_seed,
)
from lemma.common.subtensor import get_subtensor
from lemma.lean.sandbox import VerifyResult
from lemma.lean.verify_runner import run_lean_verify
from lemma.problems.base import Problem, ProblemSource
from lemma.protocol import ChallengePayload, RevealPayload
from lemma.scoring.reputation import (
    apply_rolling_outcomes,
    load_reputation,
    rolling_weights,
    save_reputation,
)
from lemma.transport.client import signed_post
from lemma.validator.weights_policy import build_full_weights

if TYPE_CHECKING:
    from lemma.common.config import LemmaSettings


_VERIFY_INFRA_REASONS = frozenset({"timeout", "oom", "docker_error", "remote_error"})


def _verify_result_is_infra_failure(vr: VerifyResult) -> bool:
    return not vr.passed and vr.reason in _VERIFY_INFRA_REASONS


def _miner_url(metagraph: bt.metagraph, uid: int) -> str | None:
    try:
        ax = metagraph.axons[uid]
    except (IndexError, AttributeError):
        return None
    ip = (getattr(ax, "ip", "") or "").strip()
    port = int(getattr(ax, "port", 0) or 0)
    if not ip or ip == "0.0.0.0" or port <= 0:
        return None
    return f"http://{ip}:{port}"


def _difficulty_weight(settings: LemmaSettings, split: str) -> float:
    key = (split or "easy").lower()
    return {
        "easy": settings.lemma_scoring_difficulty_easy,
        "medium": settings.lemma_scoring_difficulty_medium,
        "hard": settings.lemma_scoring_difficulty_hard,
        "extreme": settings.lemma_scoring_difficulty_extreme,
    }.get(key, 1.0)


async def _query_one_miner(
    *,
    client: httpx.AsyncClient,
    url: str,
    keypair: bt.Keypair,
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
        logger.debug("miner http {}: {}", r.status_code, (r.text or "")[:200])
        return None
    try:
        return RevealPayload.model_validate_json(r.content)
    except (ValueError, TypeError) as e:
        logger.debug("miner response parse error: {}", e)
        return None


async def _broadcast(
    *,
    settings: LemmaSettings,
    wallet: bt.Wallet,
    metagraph: bt.metagraph,
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
            reply = await _query_one_miner(
                client=client,
                url=url,
                keypair=wallet.hotkey,
                receiver_ss58=receiver_ss58,
                body=body,
                timeout_s=timeout_s,
            )
        return uid, reply

    out: dict[int, RevealPayload] = {}
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*(_one(uid) for uid in range(metagraph.n)))
    for uid, reply in results:
        if reply is not None and reply.proof_script:
            out[uid] = reply
    return out


def _verify_proof(
    settings: LemmaSettings,
    problem: Problem,
    proof_script: str,
) -> VerifyResult:
    try:
        return run_lean_verify(
            settings,
            verify_timeout_s=settings.lean_verify_timeout_s,
            problem=problem,
            proof_script=proof_script,
        )
    except Exception as e:  # noqa: BLE001
        return VerifyResult(passed=False, reason="docker_error", stderr_tail=str(e)[:8000])


async def run_epoch(
    settings: LemmaSettings,
    source: ProblemSource,
    *,
    dry_run: bool = False,
) -> dict[int, float]:
    """Single epoch: broadcast, verify, update rolling scores, set_weights."""
    t0 = time.perf_counter()
    wallet = bt.Wallet(name=settings.wallet_cold, hotkey=settings.wallet_hot)
    subtensor = get_subtensor(settings)
    metagraph = subtensor.metagraph(settings.netuid)
    cur_block = int(subtensor.get_current_block())
    seed_head = effective_chain_head_for_problem_seed(
        cur_block, int(settings.lemma_problem_seed_chain_head_slack_blocks or 0),
    )
    problem_seed, seed_tag = resolve_problem_seed(
        chain_head_block=seed_head,
        netuid=settings.netuid,
        mode=settings.problem_seed_mode,
        quantize_blocks=settings.problem_seed_quantize_blocks,
        subtensor=subtensor,
    )
    deadline_block, forward_wait_s = compute_forward_deadline_and_wait(
        settings=settings,
        subtensor=subtensor,
        cur_block=seed_head,
        seed_tag=seed_tag,
    )
    problem = source.sample(seed=problem_seed)
    challenge = ChallengePayload(
        theorem_id=problem.id,
        theorem_statement=problem.challenge_source(),
        imports=list(problem.imports),
        lean_toolchain=problem.lean_toolchain,
        mathlib_rev=problem.mathlib_rev,
        deadline_block=int(deadline_block),
        metronome_id=str(problem_seed),
    )

    replies = await _broadcast(
        settings=settings,
        wallet=wallet,
        metagraph=metagraph,
        challenge=challenge,
        timeout_s=forward_wait_s,
    )

    rep_store = load_reputation(settings.lemma_reputation_state_path)
    outcomes: dict[int, bool] = {}
    for uid in range(metagraph.n):
        reply = replies.get(uid)
        if reply is None:
            outcomes[uid] = False
            continue
        vr = _verify_proof(settings, problem, reply.proof_script)
        if _verify_result_is_infra_failure(vr):
            continue
        outcomes[uid] = bool(vr.passed)

    apply_rolling_outcomes(
        rep_store.rolling_score_by_uid,
        outcomes,
        alpha=settings.lemma_scoring_rolling_alpha,
        difficulty_weight=_difficulty_weight(settings, problem.split),
    )
    if not dry_run:
        save_reputation(settings.lemma_reputation_state_path, rep_store)

    weights = rolling_weights(
        {uid: rep_store.rolling_score_by_uid.get(uid, 0.0) for uid in range(metagraph.n)},
    )
    full, skip = build_full_weights(
        metagraph.n,
        weights,
        empty_policy=settings.empty_epoch_weights_policy,
        exclude_uid=None,
    )
    if not skip and not dry_run:
        subtensor.set_weights(
            wallet=wallet,
            netuid=settings.netuid,
            uids=list(range(metagraph.n)),
            weights=full,
            wait_for_inclusion=False,
        )

    logger.info(
        "epoch theorem={} seed={} verified={} weights={} skip={} elapsed={:.2f}s",
        problem.id,
        problem_seed,
        sum(1 for v in outcomes.values() if v),
        len(weights),
        skip,
        time.perf_counter() - t0,
    )
    return weights
