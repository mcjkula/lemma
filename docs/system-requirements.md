# System requirements

Rough guidance for one machine; scale for heavy workloads.

## Miner

| Resource | Notes |
| -------- | ----- |
| CPU | Few cores; inference often remote. |
| RAM | 4–8 GB typical (depends on your prover stack). |
| Disk | Small checkout + logs. |
| Network | Inbound `AXON_PORT` (default 8091); outbound to your prover API. |
| Docker | Optional for miners. |

A small VPS is often enough for a remote miner when inference is handled by an
external API provider.

## Validator

| Resource | Notes |
| -------- | ----- |
| CPU | 2+ cores. |
| RAM | **≥ 16 GB** recommended: Docker sandbox + the Mathlib workspace volume add up. |
| Disk | ≥ 20 GB for images and the `lemma-lean-cache` Docker volume (Mathlib `.lake` is ~7 GB, plus per-template warm slots up to the configured cap, default 16 GiB). |
| Docker | **Required**. The validator orchestrates a long-lived `lemma-lean-worker` container via `docker exec`. |

Cheap 4 GB VPS instances are useful for miner tests, but they are not a good
validator target once Lean verification is in the loop. Use production-like
Linux hardware with persistent SSD storage before drawing conclusions about
short theorem windows.

## Rounds and timeouts

Validator rounds follow the published problem-seed windows. With the default
100-block quantized window and ~12 s blocks, expect about 72 theorem windows
per day.

Each round broadcasts the epoch's problem(s) to all miners over Epistula HTTP,
waits up to `LEMMA_FORWARD_WAIT_MAX_S` (default 240 s) for replies, then verifies
each via `lake build`. `LEAN_VERIFY_TIMEOUT_S` defaults to 180 s — raise if
Mathlib builds legitimately exceed that on your hardware.

## Related

[validator.md](validator.md), [miner.md](miner.md), [production.md](production.md)
