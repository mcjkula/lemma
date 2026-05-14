"""Earned miner share + burn share → on-chain weight vector summing to 1.0."""

from lemma.validator.weights_policy import build_full_weights


def test_routes_burn_share_to_burn_uid() -> None:
    full = build_full_weights(4, {1: 0.7}, burn_share=0.3, burn_uid=0)
    assert abs(full[0] - 0.3) < 1e-9
    assert abs(full[1] - 0.7) < 1e-9
    assert abs(sum(full) - 1.0) < 1e-9


def test_unsolved_epoch_burns_full_budget_to_owner() -> None:
    full = build_full_weights(3, {}, burn_share=1.0, burn_uid=0)
    assert full == [1.0, 0.0, 0.0]


def test_owner_as_miner_receives_both_earned_and_burn() -> None:
    # If the owner also solved a theorem, their on-chain weight is earned + burn —
    # the chain sees one weight per UID; we sum, not max.
    full = build_full_weights(4, {0: 0.6}, burn_share=0.4, burn_uid=0)
    assert abs(full[0] - 1.0) < 1e-9
    assert full[1] == full[2] == full[3] == 0.0
    assert abs(sum(full) - 1.0) < 1e-9


def test_negative_miner_weight_clamped_to_zero() -> None:
    # compute_budget produces non-negative weights, but the function defends against
    # a malformed input by clamping at zero before composing.
    full = build_full_weights(3, {1: -0.5, 2: 0.3}, burn_share=0.7, burn_uid=0)
    assert full[1] == 0.0
    assert abs(full[2] - 0.3) < 1e-9
    assert abs(full[0] - 0.7) < 1e-9


def test_out_of_range_miner_uid_ignored() -> None:
    # A miner UID outside [0, n) is silently dropped (defensive, since
    # active_uids is set(range(n)) in run_epoch — should never happen).
    full = build_full_weights(3, {99: 0.4, 1: 0.4}, burn_share=0.2, burn_uid=0)
    assert abs(full[1] - 0.4) < 1e-9
    assert abs(full[0] - 0.2) < 1e-9
    assert abs(sum(full) - 0.6) < 1e-9  # 99's 0.4 is dropped
