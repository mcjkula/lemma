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
    """Return the UID receiving the unearned share each epoch.

    Resolution order: ``LEMMA_BURN_HOTKEY_SS58`` env override, else the subnet
    owner's hotkey from chain. Returns ``None`` when the hotkey is not registered
    on this subnet (operator misconfiguration — validator logs a warning).
    """
    ss58 = (settings.lemma_burn_hotkey_ss58 or "").strip()
    if not ss58:
        get_info = getattr(subtensor, "get_subnet_info", None)
        if callable(get_info):
            try:
                info = get_info(settings.netuid)
                ss58 = (getattr(info, "owner_hotkey", "") or "").strip()
            except Exception as e:  # noqa: BLE001
                logger.warning("burn UID resolution: get_subnet_info failed: {}", e)
                return None
    if not ss58:
        return None
    hotkeys = list(getattr(metagraph, "hotkeys", []) or [])
    try:
        return hotkeys.index(ss58)
    except ValueError:
        logger.warning(
            "burn hotkey {} is not registered on netuid {} — burn share will not route on chain",
            ss58, settings.netuid,
        )
        return None
