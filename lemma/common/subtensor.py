"""Subtensor helpers."""

from __future__ import annotations

import bittensor

from lemma.common.config import LemmaSettings


class BurnUidUnavailable(RuntimeError):
    """The synced metagraph lacks an owner hotkey we can route burn emissions to.

    The chain guarantees the owner hotkey is registered (``append_neuron`` at subnet
    creation) and immune from replacement (``replace_neuron`` refuses to evict it),
    so this only happens if the metagraph sync failed or returned a stale snapshot.
    The validator's main loop catches this and retries.
    """


def get_subtensor(settings: LemmaSettings) -> bittensor.Subtensor:
    endpoint = (settings.subtensor_chain_endpoint or "").strip()
    name = (settings.subtensor_network or "").strip()
    if endpoint:
        return bittensor.Subtensor(network=endpoint)
    if name:
        return bittensor.Subtensor(network=name)
    return bittensor.Subtensor()


def resolve_burn_uid(metagraph: bittensor.Metagraph) -> int:
    """Return the subnet owner's UID — Bittensor's primitive for emission to the owner.

    ``Metagraph.owner_hotkey`` is populated during ``Subtensor.metagraph()`` sync
    (via ``get_metagraph_info``). Per chain invariants the owner is always among
    ``metagraph.hotkeys``. Raises :class:`BurnUidUnavailable` if either guarantee
    fails — the caller (validator loop) should retry rather than ship a weight
    vector that silently absorbs the burn into miner shares.
    """
    ss58 = (metagraph.owner_hotkey or "").strip()
    if not ss58:
        raise BurnUidUnavailable(
            "metagraph.owner_hotkey is empty — sync stale or chain invariant violated",
        )
    try:
        return metagraph.hotkeys.index(ss58)
    except ValueError as e:
        raise BurnUidUnavailable(
            f"owner {ss58!r} not registered in metagraph.hotkeys — sync stale",
        ) from e
