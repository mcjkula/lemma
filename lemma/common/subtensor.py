"""Subtensor helpers."""

from __future__ import annotations

import bittensor

from lemma.common.config import LemmaSettings


def get_subtensor(settings: LemmaSettings) -> bittensor.Subtensor:
    endpoint = (settings.subtensor_chain_endpoint or "").strip()
    name = (settings.subtensor_network or "").strip()
    if endpoint:
        return bittensor.Subtensor(network=endpoint)
    if name:
        return bittensor.Subtensor(network=name)
    return bittensor.Subtensor()


def resolve_burn_uid(metagraph: bittensor.Metagraph) -> int | None:
    """Return the subnet owner's UID — Bittensor's primitive for emission to the owner.

    The chain guarantees the owner hotkey is registered (``append_neuron`` at subnet
    creation) and immune from replacement (``replace_neuron`` refuses to evict it),
    so the lookup succeeds in steady state. ``Metagraph.owner_hotkey`` is populated
    during ``Subtensor.metagraph()`` sync (via ``get_metagraph_info``), so no extra
    RPC is needed. Returns ``None`` only if the metagraph has no owner hotkey
    recorded yet — the very first block of a freshly-registered subnet.
    """
    ss58 = (metagraph.owner_hotkey or "").strip()
    if not ss58:
        return None
    try:
        return metagraph.hotkeys.index(ss58)
    except ValueError:
        return None
