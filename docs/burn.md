# The epoch budget and burn share

Every Lemma epoch starts with a budget of `1.0`. The portion paid to miners is
the portion the network *earned*; the rest burns to the subnet owner's UID.
There is no path where unearned emission flows to miners. Burn is the
structural answer to "the network produced less than full value this epoch."

## How the budget is computed

For each verified (miner, theorem) solve, the protocol assigns:

```
r = base_reward(theorem) × 0.5^rank × 0.5^pareto_layer × reign_factor(uid)
```

where

- `base_reward(t) = (1 - solve_fraction(t))²` — observed-difficulty pricing.
- `rank` is the first-to-solve rank (0 = earliest chain-stamped commit; ties
  broken by registration block).
- `pareto_layer` peels miners by their per-theorem reward vectors; layer-0
  miners are non-dominated.
- `reign_factor(uid) = (1 - 0.0033)^(reign_length - 1)` — geometric decay for
  long-running champions, ~0.33% per epoch.

Per miner: `raw_share(uid) = Σ_t r(uid, t)`. The earned share is the sum across
miners, capped at `1.0`. The burn share is `1.0 - earned`.

| Scenario | solve_fraction | base_reward | earned | burn |
|---|---|---|---|---|
| Nobody solves | 0 | 1.0 | 0.0 | **1.0** |
| 1 solver out of 5 (modest) | 0.2 | 0.64 | 0.64 | **0.36** |
| 1 solver out of 30 (hard) | 0.033 | 0.935 | 0.935 | **0.065** |
| 11 solvers out of 30 | 0.367 | 0.401 | ~1.0 (capped) | **0** |
| Everyone solves (trivial) | 1.0 | 0.0 | 0.0 | **1.0** |

## Where the burn goes

The burn share routes via `set_weights` to the subnet owner's UID, read from
`metagraph.owner_hotkey` on the synced metagraph. The chain guarantees the owner
hotkey is registered and immune from replacement, so the UID is always available.

## Consequences

1. **No incumbent free-rider.** A miner who solved heavily for ten epochs
   earns zero on an unsolved epoch, just like every other miner.
2. **Burn rate is observable.** A spike in burn signals "the network is not
   producing" and prompts intervention — easier supply, better miners.
3. **Trivial work doesn't drain the budget.** A theorem solved by 100% of
   miners has `base_reward = 0` and therefore earns nothing — the budget burns
   instead of being split among the trivial-solvers.

The protocol invariant: `Σ miner_weights + burn_share = 1.0` every epoch,
always, with no exceptions.
