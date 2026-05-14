from lemma.validator.weights_policy import build_full_weights


def test_routes_burn_share_to_burn_uid() -> None:
    full = build_full_weights(4, {1: 0.7}, burn_share=0.3, burn_uid=0)
    assert full == [0.3, 0.7, 0.0, 0.0]
    assert abs(sum(full) - 1.0) < 1e-9


def test_unsolved_epoch_burns_full_budget_to_owner() -> None:
    full = build_full_weights(3, {}, burn_share=1.0, burn_uid=0)
    assert full == [1.0, 0.0, 0.0]


def test_owner_as_miner_receives_both_earned_and_burn() -> None:
    full = build_full_weights(4, {0: 0.6}, burn_share=0.4, burn_uid=0)
    assert full == [1.0, 0.0, 0.0, 0.0]
    assert abs(sum(full) - 1.0) < 1e-9
