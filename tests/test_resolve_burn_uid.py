"""resolve_burn_uid maps the subnet owner hotkey to its UID — and refuses to fall back."""

from dataclasses import dataclass, field

import pytest

from lemma.common.subtensor import BurnUidUnavailable, resolve_burn_uid


@dataclass
class _Meta:
    hotkeys: list[str] = field(default_factory=list)
    owner_hotkey: str = ""


def test_owner_uid_is_first_when_owner_is_hotkey_zero() -> None:
    m = _Meta(hotkeys=["a", "b", "c"], owner_hotkey="a")
    assert resolve_burn_uid(m) == 0


def test_owner_uid_is_middle_index_when_owner_registered_later() -> None:
    m = _Meta(hotkeys=["a", "b", "c", "d"], owner_hotkey="c")
    assert resolve_burn_uid(m) == 2


def test_raises_when_owner_hotkey_blank() -> None:
    m = _Meta(hotkeys=["a", "b"], owner_hotkey="")
    with pytest.raises(BurnUidUnavailable, match="owner_hotkey is empty"):
        resolve_burn_uid(m)


def test_raises_when_owner_hotkey_whitespace() -> None:
    m = _Meta(hotkeys=["a", "b"], owner_hotkey="   ")
    with pytest.raises(BurnUidUnavailable, match="owner_hotkey is empty"):
        resolve_burn_uid(m)


def test_raises_when_owner_not_in_hotkeys() -> None:
    # Metagraph snapshot lag: owner_hotkey populated from get_metagraph_info but
    # axons list is one sync behind. Chain invariant violation in steady state.
    m = _Meta(hotkeys=["a", "b"], owner_hotkey="c")
    with pytest.raises(BurnUidUnavailable, match="not in metagraph.hotkeys"):
        resolve_burn_uid(m)
