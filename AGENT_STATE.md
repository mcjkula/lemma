# Agent State

This is the handoff note for chat freezes, context loss, and future agents.
Keep it short, current, and useful. The active work tracker is
[`docs/workplan.md`](docs/workplan.md).

## Working Mentality

Treat every line of code as a liability. Every line must be maintained,
reviewed, tested, and understood. Prefer lean changes that fix the underlying
shape of the system over extra layers of checks, guards, or compensating logic.

## Current Direction

Lemma's live reward axis is binary proof verification:

- a miner submits `proof_script`;
- the validator checks that proof against the published theorem with Lean;
- a proof that verifies can enter scoring;
- a proof that fails verification does not enter scoring.

Informal reasoning and optional prose-judge tooling are out-of-band. Do not add
reasoning prose, subjective judge scores, or proof-efficiency heuristics back
into the live reward path without a separate product decision.

## Current Repository State

- Working checkout: `/Users/leehall/lemma`.
- Local branch: `main` tracking `origin/main`.
- Current local working batch: 2026-05-13 audit remediation plus the
  uncommitted extreme-split problem-supply update on top of `3fabf9c`
  (`Record droplet deploy evidence`).
- Current deployed/GitHub-confirmed audit head:
  `8067b70` (`Harden set_weights result handling`), with `CI` and
  `Build and Push Docker Image` passing on GitHub Actions.
- Latest audit docs:
  - Cursor: [`docs/cursor-audit.md`](docs/cursor-audit.md), rating `7.5 / 10`.
  - Codex: [`docs/codex-audit.md`](docs/codex-audit.md), rating `8.4 / 10`.

## Local Verification Snapshot

Current local baseline after the 2026-05-13 extreme-split problem-supply update:

- `.venv/bin/ruff check lemma tests tools`: passed.
- `.venv/bin/mypy lemma`: passed,
  `Success: no issues found in 70 source files`.
- `.venv/bin/pytest tests -q`: passed,
  `314 passed, 2 skipped, 12 warnings`.
- `.venv/bin/python scripts/ci_verify_generated_templates.py`:
  `OK: generated template metadata/witness gate covered 85 builders`.
- `RUN_DOCKER_LEAN_TEMPLATES=1 LEAN_SANDBOX_IMAGE=lemma/lean-sandbox:latest .venv/bin/python scripts/ci_verify_generated_templates.py`:
  passed; all 85 generated template stubs and witnesses built in one Docker
  workspace.

## Recently Closed

- Export write failures are non-fatal after scoring; `set_weights` still runs
  when scores are already known.
- `LEMMA_VALIDATOR_MIN_FREE_BYTES` skips validator epochs before miner queries
  if root/cache disk space is too low.
- `LEMMA_LEAN_WORKSPACE_CACHE_MAX_BYTES` bounds total warm Lean workspace cache
  size in addition to the existing directory cap.
- Verifier-local `timeout`, `oom`, `docker_error`, and `remote_error` results
  are counted/exported as validator infra failures and do not downgrade miner
  verify credibility like ordinary proof failures.
- All-fail proof epochs now persist verify-credibility downgrades for ordinary
  Lean proof failures.
- Validator RPC/cadence errors stay inside the service loop; HTTP 429/rate-limit
  messages get a longer backoff.
- `set_weights` result handling now treats tuple-style false returns and raised
  RPC exceptions as failures, retries them, and logs a concrete final message
  instead of `message=None`.
- Public dashboard refreshes use `flock` and remain isolated from validator
  scoring.
- Legacy `reasoning_only`, `LEMMA_JUDGE_PROFILE_ATTEST_*`,
  `JUDGE_PROFILE_SHA256_EXPECTED`, and `/lemma/judge_profile_sha256` surfaces
  are retired.

## VPS Status Snapshot

The known testnet Droplets were updated to `8067b70` on 2026-05-13 after the
GitHub Actions run for that head passed. The validator was paused during the
fast-forward deploy, miners and Lean worker were restarted, then the validator
was started last.

- Validator / Lean worker `root@167.99.145.132`: deployed `8067b70`;
  `lemma-validator` and `lemma-lean-worker-http` active; root/cache filesystem
  `38%` used; Lean worker health returned `{"status": "ok"}`.
- Miner host `root@161.35.50.115`: deployed `8067b70`; six miner services
  active; six axon ports open; root filesystem `23%` used.
- First post-deploy validator round at `2026-05-13 07:30 UTC`:
  `theorem_id=curated/foundations/list_append_nil_induction`, `verified=3`,
  `scored=3`, `verify_infra_errors=0`, no reject counters, `seconds=369.99`,
  and `set_weights success=True`.

## Where To Work

- Active work tracker: [`docs/workplan.md`](docs/workplan.md).
- Proof objective: [`docs/objective-decision.md`](docs/objective-decision.md).
- Proof-verification incentives:
  [`docs/proof-verification-incentives.md`](docs/proof-verification-incentives.md).
- Testing commands: [`docs/testing.md`](docs/testing.md).
- VPS/key custody: [`docs/vps-safety.md`](docs/vps-safety.md).

## Rules For Future Agents

- Preserve proof-verification language: pass or fail, binary system.
- Keep binary proof eligibility separate from downstream allocation policy.
- Keep `spacetime-tao/lemma` focused on consensus-critical code.
- Use tests and real logs before changing mechanism code.
- Avoid defensive complexity where a simpler data model or call path can make
  invalid states impossible.
