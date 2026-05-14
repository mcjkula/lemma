"""Map chain head to a stable per-epoch problem seed."""

from __future__ import annotations

from typing import Literal

import bittensor
from loguru import logger

ProblemSeedMode = Literal["quantize", "subnet_epoch"]


def _quantize(chain_head_block: int, q: int) -> int:
    return (chain_head_block // max(1, q)) * max(1, q)


def first_block_of_next_seed_window(chain_head_block: int, quantize_blocks: int) -> int:
    return _quantize(chain_head_block, quantize_blocks) + max(1, quantize_blocks)


def blocks_until_quantize_boundary(chain_head_block: int, quantize_blocks: int) -> int:
    return max(1, first_block_of_next_seed_window(chain_head_block, quantize_blocks) - chain_head_block)


def problem_sample_seed_block(chain_head_block: int, quantize_blocks: int) -> int:
    return _quantize(chain_head_block, quantize_blocks)


def mix_sub_problem_seed(base_seed: int, sub_round: int) -> int:
    return base_seed + sub_round * 1_000_003


def effective_chain_head_for_problem_seed(chain_head_block: int, slack_blocks: int) -> int:
    return max(0, chain_head_block - max(0, slack_blocks))


def subnet_epoch_index_seed(chain_head_block: int, netuid: int, tempo: int) -> int:
    return (chain_head_block + netuid + 1) // (max(0, tempo) + 1)


def resolve_problem_seed(
    *, chain_head_block: int, netuid: int, mode: ProblemSeedMode,
    quantize_blocks: int, subtensor: bittensor.Subtensor,
) -> tuple[int, str]:
    if mode == "subnet_epoch":
        tempo = subtensor.tempo(netuid, block=chain_head_block)
        if tempo is None:
            return problem_sample_seed_block(chain_head_block, quantize_blocks), "quantize_fallback_no_tempo"
        return subnet_epoch_index_seed(chain_head_block, netuid, tempo), "subnet_epoch"
    return problem_sample_seed_block(chain_head_block, quantize_blocks), "quantize"


def blocks_until_challenge_may_change(
    *, chain_head_block: int, netuid: int, mode: ProblemSeedMode | str,
    quantize_blocks: int, seed_tag: str, subtensor: bittensor.Subtensor,
) -> tuple[int, str]:
    if mode == "quantize" or seed_tag == "quantize_fallback_no_tempo":
        return blocks_until_quantize_boundary(chain_head_block, quantize_blocks), "quantize_window"
    try:
        bu = subtensor.blocks_until_next_epoch(netuid)
    except Exception as e:  # noqa: BLE001
        logger.debug("blocks_until_next_epoch failed netuid={}: {}", netuid, e)
        bu = None
    if bu is not None:
        return max(1, bu), "subnet_epoch"
    return blocks_until_quantize_boundary(chain_head_block, quantize_blocks), "quantize_estimate"
