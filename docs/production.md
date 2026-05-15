# Production checklist

Prerequisites: [getting-started.md](getting-started.md).

## Lean

- Build and pin the sandbox image ([`compose/lean.Dockerfile`](../compose/lean.Dockerfile)) to match `DEFAULT_LEAN_TOOLCHAIN` / `DEFAULT_MATHLIB_REV`; use an immutable production ref ([toolchain-image-policy.md](toolchain-image-policy.md)).
- Set `LEAN_VERIFY_TIMEOUT_S`, `LEMMA_LEAN_VERIFY_MAX_CONCURRENT`, and the workspace-cache bounds (`LEMMA_LEAN_WORKSPACE_CACHE_MAX_DIRS`, `LEMMA_LEAN_WORKSPACE_CACHE_MAX_BYTES`) according to your hardware.
- Start the long-lived worker once: `bash scripts/start_lean_docker_worker.sh --update-dotenv`. The worker mounts the `lemma-lean-cache` Docker named volume at `/lemma-workspace`.

## Scoring policy

A proof must verify in Lean (allowed axioms: `{propext, Quot.sound, Classical.choice}`) to enter live scoring. The reward stack — first-to-solve rank, observed-difficulty pricing, Pareto peeling, reign decay — is documented in [docs/burn.md](burn.md) and the source under [`lemma/scoring/`](../lemma/scoring/).

## Validator settings to coordinate across operators

Align across validators (so weights are comparable):

- `LEMMA_PROBLEM_SEED_MODE`, `LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS`
- `LEAN_VERIFY_TIMEOUT_S`, `LEMMA_LEAN_VERIFY_MAX_CONCURRENT`
- `LEMMA_BLOCK_TIME_SEC_ESTIMATE`, `LEMMA_FORWARD_WAIT_MAX_S`
- `LEMMA_EPOCH_PROBLEM_COUNT`
- The sandbox image immutable ref.

See `.env.example` for the full set.

## Public proof corpus

Validators append each epoch's verified proofs to `~/.lemma/corpus/<epoch_id>.jsonl`. Optional public mirror:

```bash
uv run lemma corpus push s3://lemma-corpus/<network>/
```

## Observability

- `uv run lemma doctor` — environment, config, Lean sandbox worker, chain RPC.
- `uv run lemma weights` — chain head and netuid (debug).
- Validator log line per epoch: `epoch theorems=N solved=N earned=X.XXX burn=X.XXX miners_paid=N elapsed=X.XXs`.
- `scripts/red_team_eve.py` — pre-deployment red-team gate (Eve emission ratio ≤ 2.0).

## Cloud / VPS hosts

Running miners or validators on a VPS is allowed operationally, but it changes the risk profile.

- **Miner on VPS:** common and usually simpler than home networking because the axon has a stable public IP and port. Keep the hotkey encrypted, restrict SSH, run a firewall, and avoid storing the coldkey private file on the server.
- **Validator on VPS:** use a larger host than a cheap miner box. Validators need Docker, the `lemma-lean-cache` volume, and enough RAM/CPU for concurrent verification; a small 4 GB instance is usually miner-only or test-only.
- **Local machine:** good for development and private keys, but inbound miner ports require router/firewall setup.
- **Warm-cache lesson:** the reliable speedup path is a pinned Lean sandbox image plus the long-lived Docker worker against a Docker named volume (avoids macOS bind-mount throughput tax).

For production, prefer: coldkey private material offline/local, only hotkeys on servers, explicit `AXON_EXTERNAL_IP`, explicit firewall rules, systemd or another supervisor, and regular log review. Operator checklist: [vps-safety.md](vps-safety.md). DigitalOcean guide: [droplet-operations.md](droplet-operations.md).

## Multiple miner hotkeys on one host

One machine can run several miner hotkeys if each service has its own wallet hotkey, `AXON_PORT`, logs, and systemd unit. They can share the same checkout, but each hotkey is a separate UID on chain.

## Docker socket on validator hosts

Processes that can `docker exec` into the worker effectively have **root on the host**. Pin the sandbox image by immutable tag or digest ([toolchain-image-policy.md](toolchain-image-policy.md)), restrict who can edit `.env`, and treat the Docker socket as a **high-privilege** dependency.

## Independent security review

CI runs linters, tests, and the red-team script, but that is **not** a substitute for a focused third-party review of your deployment (Docker socket, keys, networking). Before **high-stakes mainnet** operation or large treasury exposure, budget an independent security assessment appropriate to your threat model.
