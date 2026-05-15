# Proof Verification Incentives

Lemma's reward axis is formal proof validity: miners earn for producing
Lean-valid proofs for published theorem statements, ranked by first-to-solve
and priced by observed difficulty.

## Design Objective

One sentence (litepaper-v2 §1):

> Did the miner publish, before anyone else, a Lean-kernel-verified proof of a theorem that was hard to solve this epoch?

This keeps the subnet objective close to the thing validators can reproduce:
given a locked theorem statement and a submitted `Submission.lean`, Lean either
accepts the proof under the allowed axiom set or rejects it.

## Reward Shape

1. **Eligibility:** the submitted proof must pass the pinned Lean toolchain
   (`DEFAULT_LEAN_TOOLCHAIN`) and Mathlib revision (`DEFAULT_MATHLIB_REV`), with
   no `sorry` / `admit` / `native_decide` / `unsafe` tokens and no user-declared
   axioms. Allowed axioms: `{propext, Quot.sound, Classical.choice}`.
2. **First-to-solve rank:** chain-stamped commit block orders solvers; ties
   break by earliest `block_at_registration`.
3. **Observed-difficulty pricing:** `base_reward(t) = (1 - solve_fraction(t))²`.
   Trivial theorems pay 0 — the budget burns rather than splitting among
   trivial-solvers.
4. **Rank decay:** rank-`k` solver receives `0.5^k × base_reward`.
5. **Pareto peel:** miners are peeled by per-theorem reward vectors. Layer-`k`
   miners receive `0.5^k` of the next-layer share.
6. **Reign decay:** miners atop the front for K epochs receive
   `(1 - 0.0033)^(K-1) × share`. Anti-monopoly insurance.
7. **α-rename dedup:** byte-identical proofs (after stripping comments,
   whitespace, and renaming bound variables) collapse — only the earliest commit
   counts.

The per-epoch budget invariant: `Σ miner_weights + burn_share = 1.0`. The burn
share goes to the subnet owner UID (`metagraph.owner_hotkey`).

## Current Live Rollout

The live validator path is intentionally simple: a submitted proof either passes
Lean verification for the published theorem and enters scoring, or it does not.
The scoring stack composes the six mechanisms above. Nothing else affects
miner weights.

## Out Of Scope For Rewards

- Rewriting the theorem in an easier form.
- Comment or whitespace padding (stripped by the fingerprint).
- Proof scripts that depend on user-declared axioms (rejected at axiom scan).
- Proof scripts containing `sorry`, `admit`, or `native_decide` (rejected at cheat scan).
- Extra syntax that does not improve the checked proof.

## Cadence Implications

Proof-verification scoring keeps the hot path focused on the verifier. Miner
responses can be small because a proof script is enough for scoring.

Lean verification remains the hard budget. Default `LEAN_VERIFY_TIMEOUT_S` is
180 seconds. Warm-cache verifies (template seen this epoch) complete in
seconds; cold-cache verifies copy the pre-baked mathlib `.lake` from
`/opt/lemma-stub` to the volume slot, which costs a few minutes on first use.

## Implementation

- Scoring stack: [`lemma/scoring/`](../lemma/scoring/) (`first_to_solve.py`, `pareto_subset.py`, `observed_difficulty.py`, `champion_decay.py`, `dedup.py`, `budget.py`).
- Verification: [`lemma/lean/sandbox.py`](../lemma/lean/sandbox.py) + [`lemma/lean/cheats.py`](../lemma/lean/cheats.py).
- Live composition: [`lemma/validator/epoch.py`](../lemma/validator/epoch.py).
- Budget narrative: [docs/burn.md](burn.md).
