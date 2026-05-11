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
- Current local/GitHub `main` head during the Codex audit:
  `28bbbfc8c747c46ff5d6c5b0e015e5451aeb4e58`
  (`Docs: add cursor-audit.md; CI gate pip-audit/bandit; production security note; README index`).
- `git ls-remote origin HEAD refs/heads/main` matched local `main` at
  `28bbbfc8c747c46ff5d6c5b0e015e5451aeb4e58`.
- Latest audit docs:
  - Cursor: [`docs/cursor-audit.md`](docs/cursor-audit.md), rating `7.5 / 10`.
  - Codex: [`docs/codex-audit.md`](docs/codex-audit.md), rating `7.2 / 10`.

## Local Verification Snapshot

Current local baseline from the Codex audit on 2026-05-11:

- `.venv/bin/ruff check lemma tests tools`: passed.
- `.venv/bin/mypy lemma`: passed,
  `Success: no issues found in 68 source files`.
- `.venv/bin/pytest tests -q`: passed,
  `254 passed, 2 skipped, 12 warnings`.
- `.venv/bin/python scripts/ci_verify_generated_templates.py`:
  `OK: generated template metadata gate covered 40 builders`.
- `.venv/bin/bandit -q -r lemma -ll`: passed with no medium/high findings.
- `.venv/bin/pip-audit --ignore-vuln PYSEC-2025-49 --ignore-vuln PYSEC-2022-42969`:
  passed with `No known vulnerabilities found, 3 ignored`.
- Docker Lean golden was not rerun in this pass because the local Docker daemon
  was unavailable at the configured socket.

## VPS Status Snapshot

No VPS deploy, restart, or SSH check was performed during the Codex audit doc
pass. Treat older droplet snapshots as stale until refreshed from live hosts.

## Where To Work

- Active work tracker: [`docs/workplan.md`](docs/workplan.md).
- Proof objective: [`docs/objective-decision.md`](docs/objective-decision.md).
- Proof-verification incentives:
  [`docs/proof-verification-incentives.md`](docs/proof-verification-incentives.md).
- Testing commands: [`docs/testing.md`](docs/testing.md).
- VPS/key custody: [`docs/vps-safety.md`](docs/vps-safety.md).

## Rules For Future Agents

- Preserve proof-verification language: pass or fail, binary system.
- Keep `spacetime-tao/lemma` focused on consensus-critical code.
- Use tests and real logs before changing mechanism code.
- Avoid defensive complexity where a simpler data model or call path can make
  invalid states impossible.
