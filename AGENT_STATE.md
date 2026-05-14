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

Describe the protocol as trust-minimized, not absolutely trustless. Lean checks
proof validity; registry/profile hashes align validators; hashes do not prove
problem quality, source licensing, or open-problem faithfulness. Future release
work should make third-party reruns easier through immutable image refs, hashes,
and public verification evidence.

## Current Repository State

- Working checkout: `/Users/leehall/lemma`.
- Local branch: `main` tracking `origin/main`.
- Latest pushed batch covered by this handoff: `28fb364` (`Expand generated
  supply and trust docs`) after the 2026-05-14 generated-builder expansion and
  validator-only deploy.
- Latest GitHub-confirmed runtime head: `0ff1068` (`Record CI evidence for
  set_weights cleanup`), with `CI` passing on GitHub Actions run
  `25793725075`. The preceding code commit `d95411b` also had `CI` and
  `Build and Push Docker Image` passing on runs `25793209291` and
  `25793209296`. The newer `28fb364` head has local tests and Docker Lean
  template verification recorded below, but this handoff did not re-check
  GitHub Actions.
- Current testnet Droplet head: validator / Lean worker host checkout is
  `28fb364`; the validator service was restarted. The miner host remains
  `0ff1068`.
- Latest audit docs:
  - Cursor: [`docs/cursor-audit.md`](docs/cursor-audit.md), rating `7.5 / 10`.
  - Codex: [`docs/codex-audit.md`](docs/codex-audit.md), rating `8.4 / 10`.

## Local Verification Snapshot

Current local baseline after the generated-builder expansion:

- `.venv/bin/ruff check lemma tests tools`: passed.
- `.venv/bin/mypy lemma`: passed,
  `Success: no issues found in 70 source files`.
- `.venv/bin/pytest tests -q`: passed,
  `315 passed, 2 skipped, 12 warnings`.
- `.venv/bin/python scripts/ci_verify_generated_templates.py`:
  `OK: generated template metadata/witness gate covered 100 builders`.
- Local generated registry hash:
  `b926194367c2b0ef25dd5da4179256e7b70185cf3eb0543cbc603a73a45efff3`.
- Local hybrid problem-supply hash:
  `8b7dccd4fc2a1cf68ad1e1e0ee35ea8680bdc05b24abdb7819ec1dbaee0c1556`.
- `RUN_DOCKER_LEAN_TEMPLATES=1 LEAN_SANDBOX_IMAGE=lemma/lean-sandbox:latest .venv/bin/python scripts/ci_verify_generated_templates.py`:
  passed; all 100 generated template stubs and witnesses built in one Docker
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
- Set-weights false returns without an RPC message now log
  `success=False without message` instead of tuple noise such as
  `(False, None)`.
- Legacy `reasoning_only`, `LEMMA_JUDGE_PROFILE_ATTEST_*`,
  `JUDGE_PROFILE_SHA256_EXPECTED`, and `/lemma/judge_profile_sha256` surfaces
  are retired.
- Generated problem registry now has 100 builders after the first missing-topic
  expansion batch.
- Trust-minimized design docs now distinguish proof verification, release
  alignment, Docker/toolchain pinning, public verification evidence, and
  open-problem faithfulness review.

## VPS Status Snapshot

Read-only sampling plus the follow-up deploy on 2026-05-13 moved both known
testnet Droplets to `0ff1068`. The 2026-05-14 generated-supply rollout then
fast-forwarded the validator / Lean worker host checkout to `28fb364`; miner
services were not restarted and remain on `0ff1068`.

- Validator / Lean worker `root@167.99.145.132`: checkout `28fb364`;
  `lemma-validator` active after restart; `lemma-lean-worker-http` and
  `lemma-public-dashboard.timer` remain active from the prior deploy; Lean
  worker health on `127.0.0.1:8787` previously returned `{"status": "ok"}`.
- Miner host `root@161.35.50.115`: deployed `0ff1068`; six miner services
  active.
- During the deploy, the validator failed closed on stale subnet pins after the
  extreme split changed the validator profile. Running
  `lemma configure subnet-pins --env-file /opt/lemma/.env --yes` on the
  validator host updated the profile pin to
  `85155229a2c1a0dd9537434d89a7c924368f888e4602b6d909757b09285b0a9c` and the
  problem-supply pin to
  `f4ae425ad437c97b00d47b7ba97f97e1ff4cec8d5d66290c8b2364d91f822311`.
- After the pin update and restart, validator logs showed
  `problem_source=hybrid` and the expected registry hash.
- During the `28fb364` validator rollout, an initial subnet-pins refresh run
  outside `/opt/lemma` wrote a bad profile pin and the validator failed closed.
  Rerunning from `/opt/lemma` restored profile pin
  `85155229a2c1a0dd9537434d89a7c924368f888e4602b6d909757b09285b0a9c` and set
  problem-supply pin
  `8b7dccd4fc2a1cf68ad1e1e0ee35ea8680bdc05b24abdb7819ec1dbaee0c1556`; after
  restart, the service was active and logged `problem_source=hybrid`.
- First observed post-`28fb364` validator round completed at
  `2026-05-14 05:46 UTC`: `theorem_id=gen/7117800`, split `medium`,
  `verified=3`, `scored=3`, `verify_infra_errors=0`, no reject counters, and
  `set_weights success=True`.
- First observed post-`0ff1068` round completed at `2026-05-13 10:59 UTC`:
  `theorem_id=gen/7112100`, split `medium`, `verified=5`, `scored=5`,
  `verify_infra_errors=0`, no reject counters. `set_weights` returned false
  after three attempts, but the deployed cleanup logged the operator-facing
  message as `success=False without message` instead of `(False, None)`.
- Follow-up post-`0ff1068` round completed at `2026-05-13 11:10 UTC`:
  `theorem_id=gen/7112200`, split `extreme`, `verified=2`, `scored=2`,
  `verify_infra_errors=0`, no reject counters, and
  `set_weights success=True`.
- Next live task: keep watching continued rounds for reveal/emission movement
  and any repeated false/no-message RPC pattern.

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
