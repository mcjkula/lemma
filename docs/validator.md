# Validator

Walkthrough: [getting-started.md](getting-started.md). Production validators should use the subnet-published immutable sandbox ref ([toolchain-image-policy.md](toolchain-image-policy.md)).

**Short checklist:** `bash scripts/prebuild_lean_image.sh` → `bash scripts/start_lean_docker_worker.sh` → `uv run lemma doctor` → `uv run lemma validator dry-run` → `uv run lemma validator start`. Same keys/chain setup as a miner if you run both roles.

Validator rounds follow the published problem-seed windows. The default `quantize` mode rotates every `LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS` blocks (default 100); `subnet_epoch` mode uses subnet epoch boundaries.

Validator ↔ miner transport is Epistula-signed HTTP. Validators POST `/lemma/reveal` to each miner's axon URL and collect verified proof scripts.

## What the validator does each epoch

1. Resolve the per-epoch problem seed from the chain head.
2. Build the problem batch via the supply pipeline (Streams P/M/C → freshness gate → Merkle anchor on chain).
3. Broadcast each theorem to all miners over Epistula HTTP.
4. Run each reply through the Lean sandbox (`lake build Submission` + `lake env lean AxiomCheck.lean`).
5. Apply α-rename dedup, first-to-solve ranking, Pareto-layer peeling, observed-difficulty pricing, and reign decay.
6. `set_weights` with the earned-miner shares; remainder burns to the subnet owner UID.
7. Append verified proofs to `~/.lemma/corpus/<epoch>.jsonl`.

## System requirements

- **Docker** must be installed and running. The validator orchestrates a long-lived **lemma-lean-sandbox** worker container via `docker exec` for every verify. The host filesystem is **not** used for the workspace cache — the worker mounts a Docker named volume (`lemma-lean-cache`) at `/lemma-workspace`.

### Setting up the long-lived worker

`scripts/start_lean_docker_worker.sh` creates the named volume and starts the worker:

```bash
bash scripts/prebuild_lean_image.sh         # one-time: build lemma/lean-sandbox:latest
bash scripts/start_lean_docker_worker.sh    # docker volume create + docker run -d
```

Then set `LEMMA_LEAN_DOCKER_WORKER=lemma-lean-worker` in `.env` (the script's `--update-dotenv` flag appends it for you).

### Cache bounds

Warm workspace slots are capped by `LEMMA_LEAN_WORKSPACE_CACHE_MAX_DIRS` (default 8; set 0 to disable) and `LEMMA_LEAN_WORKSPACE_CACHE_MAX_BYTES` (default 16 GiB; set 0 to disable) so growing problem variety does not fill the worker's volume. Optional `LEMMA_LEAN_WORKSPACE_CACHE_INCLUDE_SUBMISSION_HASH=true` names cache subdirs from proof text so distinct submissions never share one slot.

### Throughput

Concurrency cap: `LEMMA_LEAN_VERIFY_MAX_CONCURRENT` (default 4). Per-submission build budget: `LEAN_VERIFY_TIMEOUT_S` (default 180 seconds).

## Lean image

```bash
bash scripts/prebuild_lean_image.sh
uv run lemma validator dry-run
uv run lemma validator start
```

`dry-run` exercises the full scoring loop without `set_weights` — useful for local rehearsal.

## Compose

```bash
docker compose -f docker-compose.yml up validator
```

## Ops

[production.md](production.md).
