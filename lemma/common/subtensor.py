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
    """Return the subnet owner's UID — Bittensor's primitive for emission back to the owner.

    Reads ``owner_hotkey`` from chain each epoch and finds the matching UID on the
    metagraph. Returns ``None`` only when the owner is not yet registered on the
    subnet (expected during initial subnet bring-up).
    """
    get_info = getattr(subtensor, "get_subnet_info", None)
    if not callable(get_info):
        return None
    try:
        info = get_info(settings.netuid)
    except Exception as e:  # noqa: BLE001
        logger.warning("subnet_info lookup failed for burn UID: {}", e)
        return None
    ss58 = (getattr(info, "owner_hotkey", "") or "").strip()
    if not ss58:
        return None
    hotkeys = list(getattr(metagraph, "hotkeys", []) or [])
    try:
        return hotkeys.index(ss58)
    except ValueError:
        logger.debug("subnet owner {} not yet registered on netuid {}", ss58, settings.netuid)
        return None
