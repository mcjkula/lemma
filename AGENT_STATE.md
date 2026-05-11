# Agent State

This is the handoff note for chat freezes, context loss, and future agents.

Keep it short. The active tracker is [docs/workplan.md](docs/workplan.md).

## Working Mentality

Treat every line of code as a liability.

Every line must be maintained, reviewed, tested, and understood. Prefer simple
changes that fix the shape of the system over extra checks and guards.

## Current Direction

Lemma's live reward rule is binary proof verification:

- miner submits `proof_script`;
- validator checks it with Lean;
- passing proof can enter scoring;
- failing proof cannot receive proof score.

Informal reasoning and prose-judge tools are out of band. Do not add prose
scores, judge scores, proof-efficiency scoring, or reasoning text back into the
live reward path without a separate product decision.

## Current Repo State

- Checkout: `/Users/leehall/lemma`.
- Branch: `main`, tracking `origin/main`.
- Current local and GitHub head:
  `67dfd477c1a274e613b1ea5f01f80af24c2822ee`
  (`Fix Hatch direct refs and consolidate tracker docs`).
- The Hatch direct-reference fix is on `main`.
- GitHub CI run `25650611350` for `67dfd47` completed successfully.

## Verification Snapshot

Local checks from the Hatch fix pass:

- `uv sync --extra dev`
- `uv run ruff check lemma tests tools`
- `uv run pytest tests/ -q --ignore=tests/test_docker_golden.py`
  (`255 passed, 1 skipped, 12 warnings`)
- `uv run python scripts/ci_verify_generated_templates.py`
- Docker golden Lean verify (`1 passed in 210.60s`)
- `docker build -f Dockerfile -t lemma-runtime:ci-smoke .`

Known quality gap:

- `uv run mypy lemma` reports `70 errors in 11 files`.

## VPS Status Snapshot

Do not deploy or restart services unless the user asks.

Last checked state from the 2026-05-11 audit:

| Host | IP | Deployed commit | Running services |
| --- | --- | --- | --- |
| `lemma-lean-worker-1` | `167.99.145.132` | `82bba8d` | `lemma-lean-worker-http.service`, `lemma-validator.service` |
| `lemma-miner-1` | `161.35.50.115` | `82bba8d` | `lemma-miner.service`, `lemma-miner3.service`, `lemma-miner4.service`, `lemma-miner5.service`, `lemma-miner6.service`, `lemma-miner7.service` |

Both droplets were alive and services were active. They are behind current
`main`.

## Where To Work

- Active tracker: [docs/workplan.md](docs/workplan.md).
- Objective: [docs/objective-decision.md](docs/objective-decision.md).
- Proof rewards: [docs/proof-verification-incentives.md](docs/proof-verification-incentives.md).
- Testing: [docs/testing.md](docs/testing.md).
- VPS/key safety: [docs/vps-safety.md](docs/vps-safety.md).

## Rules For Future Agents

- Preserve the proof-pass/fail reward language.
- Keep `spacetime-tao/lemma` focused on core protocol and validation.
- Put friendly operator UX in `lemma-cli` unless core needs a small shim.
- Use tests and real logs before changing mechanism code.
- Remove invalid states by simplifying the data model or call path where
  possible.
