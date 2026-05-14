"""Subtensor helpers."""

from __future__ import annotations

import bittensor
from loguru import logger

from lemma.common.config import LemmaSettings


def get_subtensor(settings: LemmaSettings) -> bittensor.Subtensor:
    endpoint = (settings.subtensor_chain_endpoint or "").strip()
    name = (settings.subtensor_network or "").strip()
    if endpoint:
        return bittensor.Subtensor(network=endpoint)
    if name:
        return bittensor.Subtensor(network=name)
    return bittensor.Subtensor()


def resolve_burn_uid(
    settings: LemmaSettings,
    subtensor: object,
    metagraph: object,
) -> int | None:
    """Return the subnet owner's UID — Bittensor's primitive for emission to the owner.

    The chain guarantees the owner hotkey is registered (``append_neuron`` at subnet
    creation) and immune from replacement (``replace_neuron`` refuses to evict it),
    so the lookup never fails in steady state. Returns ``None`` only if the RPC
    itself fails.
    """
    get_owner = getattr(subtensor, "get_subnet_owner_hotkey", None)
    if not callable(get_owner):
        return None
    try:
        ss58 = get_owner(settings.netuid)
    except Exception as e:  # noqa: BLE001
        logger.warning("get_subnet_owner_hotkey failed for burn UID: {}", e)
        return None
    if not ss58:
        return None
    return list(metagraph.hotkeys).index(ss58)
