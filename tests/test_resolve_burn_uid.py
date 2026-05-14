"""resolve_burn_uid maps the subnet owner hotkey to its UID in the metagraph."""

from dataclasses import dataclass, field

from lemma.common.subtensor import resolve_burn_uid


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


def test_returns_none_when_owner_hotkey_blank() -> None:
    m = _Meta(hotkeys=["a", "b"], owner_hotkey="")
    assert resolve_burn_uid(m) is None


def test_returns_none_when_owner_hotkey_whitespace() -> None:
    m = _Meta(hotkeys=["a", "b"], owner_hotkey="   ")
    assert resolve_burn_uid(m) is None


def test_returns_none_when_owner_not_yet_in_hotkeys() -> None:
    # Metagraph race: owner_hotkey populated from get_metagraph_info but the
    # axons list (which produces .hotkeys) is one sync behind.
    m = _Meta(hotkeys=["a", "b"], owner_hotkey="c")
    assert resolve_burn_uid(m) is None
