"""One scoring round: broadcast theorems, compute the earned/burn budget, set weights."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import bittensor
import httpx
from loguru import logger

from lemma.common.problem_seed import effective_chain_head_for_problem_seed, resolve_problem_seed
from lemma.common.subtensor import get_subtensor, resolve_burn_uid
from lemma.protocol import ChallengePayload
from lemma.scoring.budget import compute_budget
from lemma.scoring.reputation import load_reputation, save_reputation
from lemma.supply.pipeline import build_problems_for_epoch
from lemma.transport.client import broadcast_challenge
from lemma.validator.corpus import CorpusEntry, append as append_corpus
from lemma.validator.verify import verified_solves
from lemma.validator.weights_policy import build_full_weights

if TYPE_CHECKING:
    from lemma.common.config import LemmaSettings


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


async def run_epoch(settings: LemmaSettings, *, dry_run: bool = False) -> dict[int, float]:
    t0 = time.perf_counter()
    wallet = bittensor.Wallet(name=settings.wallet_cold, hotkey=settings.wallet_hot)
    subtensor = get_subtensor(settings)
    metagraph = subtensor.metagraph(settings.netuid)
    cur_block = int(subtensor.get_current_block())
    problem_seed, _tag = resolve_problem_seed(
        chain_head_block=effective_chain_head_for_problem_seed(
            cur_block, int(settings.lemma_problem_seed_chain_head_slack_blocks or 0),
        ),
        netuid=settings.netuid, mode=settings.problem_seed_mode,
        quantize_blocks=settings.problem_seed_quantize_blocks, subtensor=subtensor,
    )
    k = max(1, int(settings.lemma_epoch_problem_count))
    problems_list, anchored_block = build_problems_for_epoch(
        settings, epoch_id=problem_seed, target_count=k, subtensor=subtensor, wallet=wallet,
    )
    if not problems_list and settings.lemma_supply_fallback_generated:
        from lemma.problems.generated import FallbackGeneratedSource

        problems_list = FallbackGeneratedSource().draw(problem_seed, k, str(problem_seed).encode("utf-8"))
        anchored_block = cur_block
    commit_block = anchored_block or cur_block
    problems = {p.id: p for p in problems_list}

    replies_by_theorem: dict[str, dict] = {}
    if problems_list:
        async with httpx.AsyncClient() as client:
            for problem in problems_list:
                replies_by_theorem[problem.id] = await broadcast_challenge(
                    client=client, metagraph=metagraph, keypair=wallet.hotkey,
                    challenge=ChallengePayload(
                        theorem_id=problem.id, theorem_statement=problem.challenge_source(),
                        imports=list(problem.imports), lean_toolchain=problem.lean_toolchain,
                        mathlib_rev=problem.mathlib_rev, deadline_block=commit_block + 1,
                        metronome_id=str(problem_seed),
                    ),
                    timeout_s=float(settings.forward_wait_max_s),
                    concurrency=settings.lemma_lean_verify_max_concurrent * 2,
                )

    solved, proofs = verified_solves(settings, problems, replies_by_theorem)
    rep_store = load_reputation(settings.lemma_reputation_state_path)
    miner_weights, burn_share = compute_budget(
        solved,
        active_uids=set(range(metagraph.n)),
        registration_block=_registration_blocks(metagraph),
        commit_block=commit_block,
        reign_by_uid=rep_store.reign_by_uid,
    )
    rep_store.reign_by_uid = {
        uid: int(rep_store.reign_by_uid.get(uid, 0)) + 1
        for uid, w in miner_weights.items() if w > 0.0
    }
    if not dry_run:
        save_reputation(settings.lemma_reputation_state_path, rep_store)

    burn_uid = resolve_burn_uid(settings, subtensor, metagraph)
    full, skip = build_full_weights(
        metagraph.n, miner_weights, burn_share=burn_share, burn_uid=burn_uid,
    )
    if not skip and not dry_run:
        response = subtensor.set_weights(
            wallet=wallet, netuid=settings.netuid, uids=list(range(metagraph.n)),
            weights=full, wait_for_inclusion=False,
        )
        if not getattr(response, "success", True):
            logger.warning("set_weights returned failure: {}", getattr(response, "message", ""))
    if not dry_run:
        append_corpus([
            CorpusEntry(
                epoch_id=problem_seed, theorem_id=tid,
                theorem_statement=problems[tid].challenge_source(), proof_script=proof,
                miner_hotkey_ss58=metagraph.hotkeys[uid], commit_block=commit_block,
                mathlib_rev=problems[tid].mathlib_rev, lean_toolchain=problems[tid].lean_toolchain,
            )
            for tid, by_uid in proofs.items() for uid, proof in by_uid.items()
        ])
    logger.info(
        "epoch theorems={} solved={} earned={:.3f} burn={:.3f} miners_paid={} skip={} elapsed={:.2f}s",
        len(problems), sum(len(v) for v in solved.values()),
        1.0 - burn_share, burn_share, len(miner_weights), skip,
        time.perf_counter() - t0,
    )
    return miner_weights
