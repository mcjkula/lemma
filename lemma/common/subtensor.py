"""Subtensor helpers."""

from __future__ import annotations

import bittensor

from lemma.common.config import LemmaSettings


class BurnUidUnavailable(RuntimeError):
    """Synced metagraph lacks ``owner_hotkey`` we can route burn emission to."""


def get_subtensor(settings: LemmaSettings) -> bittensor.Subtensor:
    return bittensor.Subtensor(network=settings.subtensor_chain_endpoint or settings.subtensor_network)


def resolve_burn_uid(metagraph: bittensor.Metagraph) -> int:
    """UID of the subnet owner. The chain guarantees the owner is registered and immune."""
    ss58 = (metagraph.owner_hotkey or "").strip()
    if not ss58:
        raise BurnUidUnavailable("metagraph.owner_hotkey is empty")
    try:
        return metagraph.hotkeys.index(ss58)
    except ValueError as e:
        raise BurnUidUnavailable(f"owner {ss58!r} not in metagraph.hotkeys") from e
