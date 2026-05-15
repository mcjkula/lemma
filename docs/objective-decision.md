# Objective Decision

This note pins the current one-sentence objective so the mechanism does not drift
into rewarding whatever the latest scoring layer happens to measure.

## One-Sentence Objective

> Did the miner publish, before anyone else, a Lean-kernel-verified proof of a theorem that was hard to solve this epoch?

No "and." Every mechanism change must preserve the answer to that question.

## Incentive Boundary

The reward path should be proof-only:

- **Eligibility:** Lean accepts the submitted proof for the locked theorem under the allowed axiom set `{propext, Quot.sound, Classical.choice}`.
- **Scoring:** rank by chain-stamped commit block (earliest wins; ties break by `block_at_registration`); price by observed difficulty `(1 - solve_fraction)²`; peel by Pareto layers; decay reign-length monopolies.
- **Allocation policy:** the redesign sums to 1.0 every epoch; what miners did not earn burns to the subnet owner UID.
- **Out of band:** informal reasoning can help humans, datasets, and debugging, but it is not a reward axis.

See [docs/burn.md](burn.md) for the concrete design.

## Why This Matters

Lean verification is objective and reproducible. The live scoring path stays
simple: publish work, verify work mechanically, pay for valid work.

## Boundary Check

Every reward change should preserve this test:

> Does this make Lean-valid theorem proving easier to measure, harder to game,
> or more economically useful?

If the answer is no, the change should not be part of the core incentive path.
See [docs/burn.md](burn.md) for the live scoring design.
