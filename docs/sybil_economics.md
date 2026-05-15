# Sybil economics and identity (operators)

Lemma scoring rewards proofs that verify in Lean. The current redesign uses α-rename fingerprint dedup + first-to-solve + Pareto-layer peeling + reign decay together. None of these prove unique humans; they limit how much a sybil pool can extract relative to a single honest miner with a real prover.

Canonical machine-readable notes: [`knowledge/sybil.realities.yaml`](../knowledge/sybil.realities.yaml).

## What Lemma actually does

| Mechanism | Module | Purpose |
| --- | --- | --- |
| **Lean verification gate** | `lemma/lean/sandbox.py` | A miner entry is reward-eligible only when its submitted proof verifies under the bounded axiom set `{propext, Quot.sound, Classical.choice}`. |
| **α-rename fingerprint dedup** | `lemma/scoring/dedup.py` | Proofs differing only in bound-variable names collapse to one fingerprint; the earliest commit wins. Identical reveals from sybils → only the first counts. |
| **First-to-solve rank with registration tie-break** | `lemma/scoring/first_to_solve.py` | Solves are ordered by chain-stamped commit block; ties break by earliest `block_at_registration`. New coldkeys lose ties to incumbents. |
| **Pareto-layer peeling** | `lemma/scoring/pareto_subset.py` | A miner is non-dominated iff no other miner has ≥ rewards on every theorem and > on at least one. Layer-0 wins full share; later layers decay by `0.5^k`. |
| **Reign decay** | `lemma/scoring/champion_decay.py` | A miner who tops the front for K consecutive epochs sees their share multiplied by `(1 - 0.0033)^(K-1)`. Anti-monopoly. |
| **Observed-difficulty pricing** | `lemma/scoring/observed_difficulty.py` | `base_reward(t) = (1 - solve_fraction(t))²`. Uniformly-solved theorems pay 0, so trivial work drains the budget into burn, not into trivial-solvers. |

The red-team gate is `eve_emission_ratio ≤ 2.0` across the scenarios in `scripts/red_team_eve.py` (replay attack, same-coldkey sybils, distinct-coldkey sybils, template enumerator, registration tiebreak).

## What does *not* exist here

- **Verified identity** — coldkeys are not proof of personhood.
- **Sybil-proof partitioning** — α-rename dedup catches byte-identical-after-renaming proofs, not distinct-prover sybils.
- **Stake-weighted miner sampling** — Lemma does not implement an extra "only query high-stake miners" policy.

## Where real economic pressure comes from (Bittensor)

Subnet **UID slots are scarce** (typically 256 per subnet). **Registration cost** responds to demand ("UID pressure"). High expected rewards → higher cost to acquire/maintain a slot; that is the primary **economic** friction against spinning up unbounded identities — not Lemma's scoring layer.

Rough equilibrium intuition (from [`sybil.realities.yaml`](../knowledge/sybil.realities.yaml)):

```text
registration_cost ≈ expected_reward_per_slot (long-run pressure)
sybil deterrent ≈ cost_of_N_slots > reward_from_running_N_parallel_miners
```

## Design guidance for subnet operators

1. **Do not** treat α-rename dedup or first-to-solve as sybil defense; they only prevent trivial copying and reward original first-solve work.
2. **Do** assume attackers can obtain **many coldkeys** if slots are cheap or rewards are high.
3. **Prefer** tasks where the useful work is the proof that verifies, not another subjective ranking signal.
4. **Run** `scripts/red_team_eve.py` before any scoring change; the Eve emission ratio gate (≤ 2.0) is the litmus.

## Decision gate before scoring changes

Do not add another sybil or reward scoring layer without red-team evidence. The default code stays simple: verified proofs become reward-eligible; ranks come from chain commit order; Pareto peels rewards; reign decay prevents monopoly.

Minimum evidence for a scoring change:

1. **UID cost context** — current registration cost, expected reward per slot, and whether the subnet is under high or low UID pressure.
2. **Red-team replay** — run `scripts/red_team_eve.py` against the proposed scoring rule. The Eve emission ratio must stay ≤ 2.0 across all scenarios.
3. **K-miner pressure** — compare one strong miner against K coordinated miners with copied, lightly rewritten, or complementary outputs in the red-team script.
4. **Accepted bypasses** — explicitly name which attacks remain acceptable for now: distinct coldkeys with distinct provers, semantic trace rewrites, etc.
5. **Rollback plan** — any scoring change must be cleanly revertible; describe how to disable in `.env` and how to roll the binary back.

## References

- α-rename + fingerprint: [`lemma/scoring/dedup.py`](../lemma/scoring/dedup.py).
- First-to-solve ranking: [`lemma/scoring/first_to_solve.py`](../lemma/scoring/first_to_solve.py).
- Pareto peel: [`lemma/scoring/pareto_subset.py`](../lemma/scoring/pareto_subset.py).
- Budget composition: [`lemma/scoring/budget.py`](../lemma/scoring/budget.py); narrative in [docs/burn.md](burn.md).
- Red-team scenarios: [`scripts/red_team_eve.py`](../scripts/red_team_eve.py).
