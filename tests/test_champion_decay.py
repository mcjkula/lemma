from lemma.scoring.champion_decay import reign_factor


def test_first_epoch_no_decay() -> None:
    assert reign_factor(0) == 1.0
    assert reign_factor(1) == 1.0


def test_factor_decays_monotonically() -> None:
    assert 1.0 > reign_factor(5) > reign_factor(50) > reign_factor(500)
