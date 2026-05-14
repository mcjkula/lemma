"""Subtensor helpers."""

from __future__ import annotations

import bittensor

from lemma.common.config import LemmaSettings


class BurnUidUnavailable(RuntimeError):
    """Synced metagraph lacks ``owner_hotkey`` we can route burn emission to."""


def get_subtensor(settings: LemmaSettings) -> bittensor.Subtensor:
    endpoint = (settings.subtensor_chain_endpoint or "").strip()
    if endpoint:
        return bittensor.Subtensor(network=endpoint)
    name = (settings.subtensor_network or "").strip()
    if name:
        return bittensor.Subtensor(network=name)
    return bittensor.Subtensor()


def resolve_burn_uid(metagraph: bittensor.Metagraph) -> int:
    """UID of the subnet owner. The chain guarantees the owner is registered and immune."""
    ss58 = (metagraph.owner_hotkey or "").strip()
    if not ss58:
        raise BurnUidUnavailable("metagraph.owner_hotkey is empty")
    try:
        return metagraph.hotkeys.index(ss58)
    except ValueError as e:
        raise BurnUidUnavailable(f"owner {ss58!r} not in metagraph.hotkeys") from e
