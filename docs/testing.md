# Testing

Clone repo and `uv sync --extra dev` ([getting-started.md](getting-started.md)).

## Default suite

```bash
uv sync --extra dev
uv run pytest tests/ -q
uv run ruff check lemma scripts tests
uv run mypy lemma
uv run python scripts/red_team_eve.py
```

No API keys or Docker are needed for the default suite. The live Lean kernel
integration test (`tests/test_lean_kernel_integration.py`) is opt-in and
skipped unless explicitly enabled.

## Live Lean kernel integration test

Requires Docker + the prebuilt sandbox image + a running worker container.

```bash
docker build -f compose/lean.Dockerfile -t lemma/lean-sandbox:latest .
docker volume create lemma-lean-cache
docker run -d --name lean-worker \
    -v lemma-lean-cache:/lemma-workspace \
    lemma/lean-sandbox:latest sleep infinity
LEMMA_LEAN_INTEGRATION=1 \
LEMMA_LEAN_DOCKER_WORKER=lean-worker \
    uv run pytest tests/test_lean_kernel_integration.py -v
```

The first run cold-bootstraps mathlib into the volume (a few minutes on Linux;
~5 minutes total on macOS Docker Desktop). Subsequent runs reuse the warm cache.

## Red-team gate

```bash
uv run python scripts/red_team_eve.py
```

Asserts `eve_emission_ratio ≤ 2.0` across replay attack, sybil pools
(same-coldkey and distinct-coldkey), template enumerator, and
registration-tie-break scenarios. CI gates this.

## Sandbox image

The integration test and production validators use the same image:

```bash
docker build -f compose/lean.Dockerfile -t lemma/lean-sandbox:latest .
```

Production should use a subnet-published immutable tag or digest, not the
mutable local `latest` tag ([toolchain-image-policy.md](toolchain-image-policy.md)).
