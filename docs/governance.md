# Governance and upgrades

Lean verification is objective; validator scoring must stay deterministic and coordinated. Coordinate visible behavior off-chain.

## Problem supply

Validators map block seed → theorem batch via the supply pipeline ([`lemma/supply/pipeline.py`](../lemma/supply/pipeline.py)): Streams P (perturbed Mathlib), M (Mathlib `sorry`s), C (competition autoformalisations) → freshness gate → Merkle root anchored on chain via `set_commitment`. Stake-weighted Yuma consensus on the root means honest validators agree, dishonest ones get clipped.

Consensus needs the same release: same Git tag, same Lean toolchain (`DEFAULT_LEAN_TOOLCHAIN` in `lemma/lean/__init__.py`), same Mathlib revision (`DEFAULT_MATHLIB_REV`), same `data/mathlib_seeds.jsonl`, same seed-window cadence.

## Validator scoring profile

The scoring path is documented in [docs/burn.md](burn.md):

```
r(uid, t) = base_reward(t) × 0.5^rank × 0.5^pareto_layer × reign_factor(uid)
```

with `base_reward(t) = (1 - solve_fraction(t))²`. The per-epoch budget invariant: `Σ miner_weights + burn_share = 1.0`.

The reward-relevant configuration: `LEMMA_PROBLEM_SEED_MODE`, `LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS`, `LEAN_VERIFY_TIMEOUT_S`, `LEMMA_FORWARD_WAIT_MAX_S`, `LEMMA_BLOCK_TIME_SEC_ESTIMATE`, `LEMMA_EPOCH_PROBLEM_COUNT`. Validators are expected to share these.

## Sybil and multi-account incentives

α-rename dedup + first-to-solve registration tie-break + Pareto-layer peeling + reign decay together limit how much a sybil pool can extract relative to a single honest miner with a real prover. The red-team gate is `eve_emission_ratio ≤ 2.0` (`scripts/red_team_eve.py`). Read [sybil_economics.md](sybil_economics.md) before treating coldkeys as identity.

## Wire transport

Validator ↔ miner calls use Epistula-signed HTTP (`lemma/transport/epistula.py`): timestamp + nonce + sha256(body) bound by a Sr25519 signature over the canonical request. Replay-protected by a bounded FIFO of `(sender, uuid)` pairs. 60-second timestamp window.

## Shared validator settings

The **subnet operator** publishes one configuration for the subnet: cadence, timeouts, sandbox image. Validators are expected to deploy **that** template so scores stay comparable. Document and distribute: `LEMMA_BLOCK_TIME_SEC_ESTIMATE`, `LEMMA_FORWARD_WAIT_MAX_S`, `LEAN_VERIFY_TIMEOUT_S`, `LEMMA_PROBLEM_SEED_MODE`, `LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS`, `LEMMA_LEAN_VERIFY_MAX_CONCURRENT`, sandbox image ref. Nothing here is "per-validator preference." On-chain code does not enforce equality — parity relies on the published policy.

### Parity checklist

1. Pin one Git tag and one immutable sandbox image ref ([toolchain-image-policy.md](toolchain-image-policy.md)).
2. Publish a shared `.env` template (see `.env.example`).
3. Announce upgrades with changelog and cutover block.

## Trust-minimized release evidence

Every live rollout should publish enough evidence for another operator to reproduce the verifier and compare config:

- Git commit and release tag;
- sandbox image immutable ref, preferably a digest;
- Lean toolchain and Mathlib revision;
- `data/mathlib_seeds.jsonl` checksum;
- cutover block/window and rollback release.

The public proof corpus (`~/.lemma/corpus/<epoch>.jsonl`, optionally mirrored via `lemma corpus push s3://...`) makes individual rounds rerunnable: theorem id, statement, submitted proof, miner hotkey, commit block, Mathlib rev, Lean toolchain. Avoid adding protocol machinery until the minimal public evidence format is clear.

## Miner axon policy

Miners advertise their axon URL on chain via `serve_extrinsic`. Validators iterate the metagraph, POST `/lemma/reveal` with Epistula headers. Body size is capped by `LEMMA_INBOUND_MAX_CHARS` on the miner side.
