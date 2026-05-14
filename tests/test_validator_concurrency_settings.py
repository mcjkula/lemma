"""Network-coordination defaults must match across validators."""

from lemma.common.config import LemmaSettings


def test_quantize_blocks_default_is_load_bearing() -> None:
    # Validators must agree on this default; differing values yield different
    # theorem seeds per epoch and split the network.
    assert LemmaSettings().problem_seed_quantize_blocks == 100
