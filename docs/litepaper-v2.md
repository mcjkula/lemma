# Lemma — A Market for Kernel-Verified Mathematics

**Lemma is a Bittensor subnet that pays miners to produce kernel-verified Lean proofs of hard, fresh theorems.**

The Lean kernel is the only judge. Each epoch has a fixed budget. The portion of that budget paid to miners equals the share they earned by producing verified proofs; the rest burns to the subnet's treasury. Past glory does not earn future emission — every epoch settles on what was actually produced.

Bitcoin's miners are paid to securitize blockspace. Bittensor's miners are paid to produce useful intelligence. Lemma's miners are paid to produce kernel-verified proofs of theorems that did not have a known proof at the start of the epoch. The work is different, but the pattern is familiar: open participants compete under public rules, and the network rewards work that can be checked.

## The Short Version

A theorem is a precise mathematical claim. A proof is a correct argument for that claim. On Lemma, proofs are written in Lean, a language designed so software can verify each step.

A Lemma round works like this:

1. Validators draw the epoch's theorem batch and anchor its Merkle root on chain via `set_commitment`. The chain block at which the batch is anchored is the canonical "epoch start" timestamp for every miner.
2. The subnet publishes the theorems. Miners use their own AI prover to write Lean proofs.
3. Miners send commitments and full proofs to validators over signed HTTP. Each proof is α-renamed and fingerprinted on arrival, so byte-clones of an earlier proof are dropped without earning.
4. Validators run the Lean kernel on each submission. The earlier-registered hotkey breaks ranking ties on the same theorem.
5. Verified proofs earn a share of the epoch's budget. Whatever fraction the network did not earn burns to the subnet owner.

There is no judge, no rubric, no reasoning grade, no compute multiplier. The mechanism asks one question and pays one signal: *did the miner publish, before anyone else, a Lean-kernel-verified proof of a theorem that was hard to solve this epoch?*

## Why Proofs?

Mathematics is one of the foundations under science, cryptography, algorithms, software, physics, engineering, and AI reasoning. Better theorem proving produces solved problems, stronger reasoning systems, new training data, and a public record of computer-verified mathematical work.

Lemma does not need a revenue story to matter. Its value is the work it coordinates: verified mathematical progress, accumulated one proof at a time, in public. How valuable that is should be decided by the market, the same way markets decide how much they value Bitcoin's security or Bittensor's intelligence.

## Why Lean?

Lean is a proof assistant: software for writing mathematics in a form computers can check. Think of it as a strict compiler for proofs.

If a miner submits prose that sounds convincing, Lean does not care. If the Lean file proves the exact theorem under the pinned rules, it passes. If it changes the goal, leaves work unfinished, uses a banned shortcut such as `sorry`, or does not type-check, it fails.

In Lean, `sorry` is a placeholder for an unfinished proof. It is useful while someone is still writing, but it is not a real proof for Lemma. An axiom is an extra assumption that the proof's author adds. If miners could add their own axioms, they could change the rules instead of proving the theorem. Lemma rejects both shortcuts and pins the allowed axiom set to a small classical core: `propext`, `Quot.sound`, and `Classical.choice`. Any proof that depends on something outside that set is rejected.

That mechanical gate is what makes the subnet credible. Validators do not need to decide whose explanation sounded best. They run the checker.

## Why Bittensor?

Bittensor provides open miner participation, validator scoring, chain-visible weights, and token rewards. Lemma uses that structure for a task with an objective check.

The pairing is simple:

- Bittensor coordinates the network.
- Lean checks the work.
- Lemma points the incentive structure at theorem proving.

Lemma is structurally the cleanest possible Bittensor subnet: the validator's job is to run a deterministic checker that every other validator agrees with. Consensus reduces to a notary.

## The Commodity

Bitcoin's commodity is blockspace, scarce because the protocol enforces a difficulty target. Lemma's commodity is **kernel-verified Lean proofs of theorems that did not have a known proof in this exact form at the start of the epoch.**

The five qualities that make it a commodity:

- **Kernel-verified.** The Lean kernel is a small, deterministic checker. Every honest validator gets bit-identical verdicts on the same proof against the same Mathlib version.
- **Lean proofs.** The artifact is a Lean source file that closes the theorem with an explicit proof script. No `sorry`, no new axioms, no unsafe shortcuts.
- **Theorems, not exercises.** A theorem in Lemma's sense is non-trivial: no single Mathlib lemma closes it, and no off-the-shelf basic tactic closes it inside a short budget.
- **Fresh.** The theorem's exact form was not on the public Internet at the start of the epoch. The supply pipeline checks this against a public-corpus index before publishing.
- **At the start of the epoch.** Time is the chain. Theorems are pinned to a chain block, proofs are pinned to a chain block, and emissions are settled at the end of the epoch on a kernel that does not depend on wallclock.

This commodity is non-fungible per theorem (a proof of *X* is not a proof of *Y*), fungible across theorems within a difficulty band (proving any equally-hard *X* or *Y* is equally valuable), and Pareto-comparable across miners (a miner who proved *X* and *Y* dominates one who proved only *X*).

That shape dictates how the commodity is priced.

## What Counts As Work?

Each epoch publishes one theorem. Before it reaches miners, the theorem passes three gates.

**Kernel-well-formed.** The validator builds the theorem's statement, with the proof body left as `sorry`. If Lean rejects the statement as malformed, it never enters the supply.

**Non-trivial.** The validator tries to close the theorem with a stack of basic Lean tactics: `decide`, `simp_all`, `omega`, `polyrith`, `norm_num`, `exact?`. Each gets up to 30 seconds. If any of them succeeds, the theorem is too easy and the validator draws another.

**Fresh.** The theorem's normalized statement (variable names α-renamed, whitespace collapsed) is hashed and checked against an on-chain registry of every theorem the subnet has published, and against an off-chain bloom filter built from public Lean corpora. If the hash matches anything in those, the theorem is rejected as already-known.

Theorems that pass all three gates are drawn from three streams, weighted 60 / 25 / 15 at launch:

- **Stream P — Perturbed Mathlib (≈ 60%).** A curated library of ~900 well-known math statements (commutativity, list identities, inequalities, propositional logic). Each has parameter slots — constants, variable names, hypothesis order. At each epoch, a per-epoch random seed (derived from the chain head) fills the slots. The result is mathematically routine but syntactically novel. The full template space is large enough that pre-caching answers is infeasible.
- **Stream M — Open Mathlib `sorry`s (≈ 25%).** Mathlib contains hundreds of placeholder lemmas marked `sorry` — real research problems that mathematicians have not yet proved. A daily crawler exposes these to the supply pool. A miner who closes one has also produced a Mathlib pull-request candidate.
- **Stream C — Competition formalizations (≈ 15%).** Competition-style problems autoformalised into Lean. Drawn at a slower rate. Used as a difficulty anchor when Stream P starts solving in seconds.

The supply pipeline is what makes the mechanism work. Hard supply makes scoring trivial. Easy supply breaks any scoring rule.

## The Race

Each epoch is anchored on chain by a single validator-side `set_commitment` call that stamps the epoch's theorem-batch Merkle root with a finalised block number. That block is the shared "when did this epoch start" timestamp every miner inherits. From there, the race plays out off-chain over signed HTTP.

```
[validator anchors batch on chain] → [miners prove, submit commits + reveals over HTTP] → [validators verify, settle]
```

Miners receive the theorems and compute proofs with their own provers. When a miner has one, it sends two signed HTTP requests to validators: a commit (the SHA-256 of the proof concatenated with a random nonce) and, once the commit is acknowledged, the full proof. Both messages travel through Epistula — a standard signing scheme that binds each message to its sender, receiver, body, and a timestamp + nonce — so validators can prove who sent what.

Validators check that the proof hashes to its commitment, then run the Lean kernel. Verified proofs are α-renamed and fingerprinted: variable names are normalized and whitespace collapsed, so byte-clones of an earlier proof collide on fingerprint. The first arrival keeps the proof; later identical submissions are dropped before they enter the scoring rule.

Two miners who both find a proof — only one is first. The rank-0 reward goes to the proof whose fingerprint was seen first by the validators. Ties on the same theorem break by the earlier-registered hotkey, the same incumbency rule other Bittensor subnets use to suppress sybil farms.

This is deliberately the lightest possible ordering layer: one chain stamp per epoch (the batch root), HTTP arrival within the epoch, α-rename to handle copyists, and registration block as the deterministic tie-break. The chain anchor pins the epoch; α-rename pins authorship; the validator's Lean kernel pins correctness.

## Scoring: One Question, One Answer

Lemma's scoring has one question and four layers that all answer it.

**Question:** *Did the miner publish, before anyone else, a Lean-kernel-verified proof of a theorem that was hard to solve this epoch?*

**Layer 1 — Observed-difficulty pricing.** For each verified solve, the miner earns

```
reward = base_reward(theorem) × 0.5 ^ rank
```

where `rank` is the first-to-solve position (0 for the earliest commit) and `base_reward(theorem) = (1 − solve_fraction)²`. A theorem solved by 1% of miners has `base_reward ≈ 0.98`. A theorem solved by 90% has `base_reward ≈ 0.01`. Trivial work earns near-zero by construction.

**Layer 2 — Pareto subset domination.** Aggregate each miner's per-theorem rewards into a vector. Miners are peeled into Pareto layers: layer 0 is the set of miners not strictly dominated by any other (their reward vector is on the frontier). Layer 1 is the next peel, layer 2 the next, and so on. Layer-*k* miners earn their share multiplied by `0.5 ^ k`. This rewards solving *different* theorems, not just *more* theorems.

**Layer 3 — Proof fingerprint dedup.** Two miners who submit byte-identical proofs — after stripping comments, collapsing whitespace, and α-renaming bound variables — collide on fingerprint. The system keeps only the earliest commit; later identical submissions are dropped. A copy of someone else's proof earns nothing.

**Layer 4 — Champion-reign decay.** A miner that earned positive weight for *K* consecutive epochs has its share multiplied by `(1 − 0.0033) ^ (K − 1)`. Anti-monopoly insurance: even a genuinely-best miner slowly loses share if it dominates too long.

The four layers compose. A miner who is first on a hard theorem with a unique proof earns nearly the whole budget. A copy earns nothing. A long-time champion earns a little less each epoch.

## The Budget and the Burn

Every epoch starts with a budget of `1.0`. The portion paid to miners equals the share they earned; the rest burns to the subnet's burn hotkey. The protocol invariant is:

```
sum(miner_weights) + burn_share = 1.0
```

This holds every epoch, with no exceptions.

### How the earned share is computed

Apply the four scoring layers to each verified solve, then sum across all miners. Cap at `1.0`. The cap rarely matters in practice — typical epochs leave a positive burn share, and the cap only activates when many miners solve a hard theorem together.

Worked scenarios on a 30-miner network with one theorem per epoch:

| Scenario | Solvers | Base reward | Earned share | Burn share |
|---|---|---|---|---|
| Nobody solves a hard theorem | 0 | 1.0 | 0.0 | **1.0** |
| One miner solves a hard theorem | 1 | 0.935 | 0.935 | **0.065** |
| Three miners solve a moderate one | 3 | 0.81 | ~1.0 (capped) | **0.0** |
| Eleven miners solve an easier one | 11 | 0.401 | ~1.0 (capped) | **0.0** |
| Everyone solves a trivial one | 30 | 0.0 | 0.0 | **1.0** |

### Where the burn goes

The burn share routes to the subnet owner's UID — Bittensor's standard primitive for sending emission back to the subnet owner. The validator reads `owner_hotkey` from chain at the start of each epoch and finds the matching UID on the metagraph. Nothing else is configured: no separate burn address, no treasury hotkey, no override.

### What the budget guarantees

The economic principle is one line: **emission is something a network earns, not something the protocol owes.** Lemma treats each epoch as a chance for the network to earn its budget. What it does not earn, it does not get. Three properties follow from that invariant.

**Past winners are paid only for current work.** A miner that topped the budget for ten epochs earns zero on an unsolved epoch, just like every other miner. Each epoch settles on what was actually produced.

**The burn rate is the cleanest single health metric.** A subnet observer can ask: *what fraction of last week's budget actually paid for verified proofs?* The answer is `1 − mean(burn_share)`. A high number means the network is healthy; a low number means something specific needs fixing — improve the supply, raise rewards, escalate to the future bounty channel.

**Trivial work cannot drain the budget.** A theorem solved by every miner has `base_reward = 0` and earns nothing. The budget burns instead of being split among the trivial-solvers. The feedback loop is self-correcting: when supply gets too easy, the burn share signals it.

## Sybil Resistance

A sybil farm runs *N* hotkeys with the same prover. Under Lemma's mechanism, *N* does not scale emissions.

**UID slot scarcity.** A subnet has at most 256 UIDs. Each sybil occupies one. Adding more requires displacing real miners via Bittensor's burned-registration cost, which rises with registration pressure.

**Incumbency tie-break.** All *N* sybil hotkeys commit at almost the same block. The protocol breaks the tie by the earlier-registered hotkey: the oldest gets rank 0; the rest fall to ranks 1, 2, 3 with `0.5 ^ k` decay. Their combined share is bounded by a geometric series — roughly twice the single best hotkey's share, regardless of *N*.

**Proof fingerprint dedup.** Identical proofs collapse to one entry. The geometric series collapses entirely: only the earliest commit gets paid.

These three layers compose. *N* sybil hotkeys earn at most one well-tuned hotkey's worth of emission. To earn more, the attacker must write a second prover that solves *different* theorems — which is precisely what the network wants.

## A Concrete Example

The supply draws a Stream P perturbation. The template is

```
∀ a b : Nat, a + b = b + a
```

and the per-epoch seed renders constants `a = 7`, `b = 13`. The published theorem becomes:

```lean
import Mathlib

theorem t_perturb_add_comm_a4f2c9 : (7 : Nat) + 13 = 13 + 7 := by
 sorry
```

This is mathematically routine — Lean's `Nat.add_comm` would close it in one line — but the freshness gate confirms `(7 : Nat) + 13 = 13 + 7` was not in any public corpus.

The baseline tactic filter tries `decide`, `simp_all`, `omega`, `norm_num`, and `exact?`. They all close it. **The theorem is rejected from supply** and the validator draws another.

When a Stream P perturbation does survive the baseline filter — for example a polynomial identity that `polyrith` cannot crack — it is published. Miners receive the theorem, compute proofs with their own provers, commit hashes on chain, and reveal proofs over HTTP. The validator runs Lean on each revealed proof under the pinned toolchain. Proofs that pass the kernel and use only the allowed axioms become eligible for the epoch's budget. The budget settles per the scoring rule; the unearned share burns.

## What Miners Do

A miner receives a theorem statement and returns a Lean proof script.

How the proof is found is the miner's business: closed-source LLM, open-source LLM, classical theorem prover, hybrid, tactic search, retrieval over Mathlib. Lemma ships no reference prover and provides no canonical solution. Operators bring their own solver; the miner skeleton's empty default returns nothing.

The proof script is the only reward-critical artifact. There is no reasoning trace, no model card, no chain-of-thought to grade.

Running Lean locally before committing can catch errors before they cost an epoch. The validator's check is what matters for scoring.

## What Validators Do

A validator's job is to publish theorems, collect commits, verify proofs, and settle the budget.

Validator verification runs Lean inside a Docker container against the pinned toolchain. The same toolchain and Mathlib version run on every validator, so the kernel verdict is the same everywhere. Disagreements with the kernel are statistical impossibilities except via misconfiguration, which the chain's stake-weighted consensus clips automatically.

A validator does not run an LLM. It does not score reasoning. It does not maintain a rubric. It runs `lake build` and reads the exit code.

## The Public Corpus

Every kernel-verified proof, once revealed, is appended to a per-epoch JSONL file in the validator's local corpus. Operators who opt in publish the corpus to public storage. The corpus is the product Lemma produces: a growing, publicly-verifiable formal-math dataset.

The corpus has three audiences:

- **Mathlib.** Stream M proofs (open `sorry`s) are pre-formatted as pull-request candidates. A side process submits them upstream. If Mathlib accepts the PR, the subnet records that fact in a public ledger — as a reputation signal for the subnet, not as an emission multiplier.
- **The Lean prover ecosystem.** Open provers use the corpus as a training and evaluation set. Every published proof is a public artifact anyone can use.
- **Customers (future).** External parties post Lean theorem statements with escrowed bounties. The first valid proof wins the escrow plus the standard emission share. This becomes a real demand-side channel in a later phase.

Miners who want their proofs kept private may opt out of publication. Opted-out proofs do not count for emission.

## Roadmap

The mechanism described above is what Lemma ships at launch. Three further phases are planned.

- **Phase 0 — Bootstrap.** Stream P supply, kernel-only validators, the burn budget mechanism, Epistula-signed HTTP transport, validator-side chain anchoring of the epoch batch. This is the current shipped design.
- **Phase 1 — Supply maturity.** Stream M (Mathlib `sorry` crawler) and Stream C (competition autoformalizations) reach steady-state. The freshness bloom filter is rebuilt monthly. Stream P seed corpus expands to reduce enumeration risk.
- **Phase 2 — Customer bounties.** External parties post theorems with escrowed prizes. The first valid proof wins. A Mathlib-bridge bot opens upstream PRs from Stream M solves.
- **Phase 3 — Distributed verification.** Miners run Lean inside TEE-attested containers. Validators verify only a random sample. Validator compute drops to a small fraction of current levels.

## Start Here

Operators wanting to run miners or validators should start with the operations guides under `docs/`. The mechanism itself is fully specified by this document and the implementation in `lemma/`.

---

## Appendix A — What Changed from the Live Mechanism

The mechanism documented in `docs/litepaper.md` — binary Lean-pass over generated templates, smoothed via EMA, normalized, coldkey-partitioned — accurately describes what Lemma was. This appendix lists what changed, why, and what each change replaces.

The motivating observation was that the Lean kernel is a perfect oracle, but a perfect oracle is only as informative as the questions it is asked. The original supply was a fixed catalog of ~100 procedurally-generated templates, each closeable by a single Mathlib lemma. The kernel said *yes* to every honest miner. *Yes for everyone* is not a ranking signal, so no scoring rule on top of that supply could discriminate.

The redesign is one structural move — *make supply hard* — with consequences across the rest of the system:

| Live mechanism | Redesigned mechanism | Reason |
|---|---|---|
| Procedurally-generated templates, enumerable from the open-source code | Streams P / M / C: perturbed Mathlib, open `sorry`s, competition problems | The original templates were lookup tables; the new supply is unenumerable |
| Binary pass/fail per theorem, smoothed via EMA across epochs | First-to-solve ranking with observed-difficulty pricing per theorem | Binary pass/fail saturates at 1.0 for every honest miner; there is no ranking signal in a uniform distribution |
| Coldkey-partition collapses same-coldkey hotkeys | No coldkey-based defense; sybils handled by registration cost + incumbency tie-break + proof dedup | Coldkey-dedup is unenforceable (sybils use different coldkeys); the new layers do not depend on `coldkey ↔ entity` being injective |
| LLM judge surface (orphaned but present) | The Lean kernel is the only judge | LLM-as-judge is gameable, expensive, and adds an attack surface that the kernel makes unnecessary |
| `bt.Synapse` Python-only transport | Epistula-signed HTTP | The legacy transport is deprecated and language-locked; standard HTTP works in any language |
| Process-local commit-reveal cache | Validator-side chain anchor of the epoch batch (`set_commitment`) + α-rename fingerprinting on HTTP arrival | The in-memory cache was memory-DoS-able and not durable across restarts; one chain anchor per epoch plus arrival-order dedup gets every property the cache provided without re-implementing chain primitives |
| Skip-set-weights on empty epochs — previous winners persist | Burn the unearned share to the subnet's burn hotkey each epoch | "Skip" silently rewards incumbents for the network's failure; burn aligns emission with productivity |
| No freshness check | On-chain registry of past Lemma theorems + bloom filter of public corpora | Without freshness, a "fresh" theorem can be a republish of a Mathlib lemma whose proof every miner has |
| No triviality filter | Baseline tactic stack rejects easy theorems before publication | Without a triviality filter, easy theorems flood the supply and the budget pays for cookie-and-cream work |
| Single-blob `lemma/` package, ~12k lines | Slim package, ~3k lines | Each axis the old design measured was a deletion candidate; deleting them shrinks the surface dramatically |

The redesign is roughly half the package by line count. The remaining half does fewer things, but more clearly.

## Appendix B — The Burn Budget in Detail

This appendix works through the math of the burn mechanism for readers who want the exact arithmetic.

### The budget invariant

Each epoch has a budget of `1.0`. For each verified `(miner, theorem)` solve, define

```
r(miner, theorem) = base_reward(theorem)
     × 0.5 ^ rank(miner, theorem)
     × 0.5 ^ pareto_layer(miner)
     × reign_factor(miner)
```

where the four multiplicative factors are observed difficulty, first-to-solve rank decay, Pareto layer decay, and champion-reign decay. The earned share is

```
earned = min(1.0, sum of r(miner, theorem) over all verified solves)
burn = 1.0 − earned
```

The cap exists because the geometric sum over the ranks 0..9 is bounded by `2`, and several Pareto layers can contribute. In practice the cap rarely activates: when many miners solve a theorem, observed difficulty drops and `base_reward → 0`; when few solve, the sum is well under `1.0`.

### Worked scenarios

**Single solver, hard theorem.** Network of 30 miners; one solves; the others fail. `solve_fraction = 1/30 ≈ 0.033`. `base_reward = (1 − 0.033)² ≈ 0.935`. The solver is rank 0, layer 0, no reign decay. `r = 0.935`. Earned 0.935; burn 0.065. The solver receives ~93.5% of emission; ~6.5% routes to the burn hotkey.

**Single solver, modest theorem.** Network of 5 miners; one solves; four fail. `solve_fraction = 0.2`. `base_reward = 0.64`. Earned 0.64; burn 0.36.

**Three solvers, moderate theorem.** Network of 30; three solve; everyone else fails. `solve_fraction = 0.1`. `base_reward = 0.81`. The three solvers tie on commit block; registration order breaks the tie. Ranks 0, 1, 2 — rewards 0.81, 0.405, 0.2025. Pareto layers peel them apart (each strictly dominates the next), so the per-layer decay applies: `0.81 + 0.405 × 0.5 + 0.2025 × 0.25 ≈ 1.06`. Capped at 1.0; burn 0.

**Everyone solves a trivial theorem.** `solve_fraction = 1.0`. `base_reward = 0`. Nobody earns anything; burn 1.0.

**Nobody solves.** No verified solves to sum. Earned 0; burn 1.0.

**Long-running champion on a hard theorem.** A miner with 1000 consecutive epochs of positive weight has `reign_factor = (1 − 0.0033) ^ 999 ≈ 0.037`. Even on a theorem they would have won outright as a newcomer, they earn ~3.7% of the fresh-miner share. The remaining ~96% burns.

### Why this is the right shape

A protocol that always pays full emission regardless of work produced treats emission as a guaranteed entitlement. That model invites stagnation: incumbents extract emission without continuing to produce, and new entrants face no genuine reward gradient because every epoch's pool is already committed.

A protocol that burns the unearned share treats emission as something the network has to earn each epoch. The reward gradient is sharp: producing more, harder work earns more emission; producing nothing earns nothing — including for past winners. Burn is what aligns the economic feedback loop with the design intent.

### Routing

Each epoch the validator reads `subtensor.get_subnet_info(netuid).owner_hotkey` and finds its UID on the metagraph. The unearned share is published as weight on that UID. This is the same chain primitive other Bittensor subnets use to send emission to the owner; Lemma adds nothing on top.

## Appendix C — Open Uncertainties

The redesign rests on three empirical bets that may need recalibration over time.

**Stream P perturbation cardinality.** The launch seed corpus is ~900 statements with parameter slots, producing a template space in the 10⁵–10⁶ range. If miners build provers that effectively pre-cache the full space, the supply becomes enumerable and the freshness gate degrades. The mitigation is to expand the seed corpus (an ongoing curation effort) and to increase Stream M / C weight as Stream P becomes too easy.

**Baseline tactic budget.** The 30-second budget for the non-triviality filter is a starting guess. If too many theorems fall through, the supply collapses; if too few do, the supply is too easy. The right value is determined empirically during the bootstrap phase.

**First-to-solve under network latency.** Commits are timestamped at chain inclusion, not HTTP arrival, which bounds latency-gaming to chain-block granularity (~12 seconds). For hard theorems where prover time dominates, this is fine. For easy theorems where multiple miners solve in seconds, the race may degenerate into a network-topology contest. The observed-difficulty pricing pushes against this — when many miners solve a theorem, the reward collapses toward zero — but the dynamic is worth monitoring.

The mechanism is built so these uncertainties can be tuned without redesign. Supply ratios, baseline budget, and burn governance are all configuration knobs around an unchanged scoring core.
