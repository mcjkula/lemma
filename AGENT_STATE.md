# Agent State

This is the handoff note for future agents working in `/Users/leehall/lemma-wta`.
Keep it short, current, and useful.

## Working Mentality

Treat every line of code as a liability. Every line must be maintained,
reviewed, tested, and understood. Prefer lean changes that fix the underlying
shape of the system over extra layers of checks, guards, or compensating logic.

## Current Direction

Lemma is a winner-take-all known-theorem formalization subnet.

The live reward path is:

- one ordered known-theorem target is active at a time;
- miners submit `proof_script`;
- validators verify the proof with Lean against the locked target;
- the first passing solver is appended to the WTA ledger;
- the current champion receives 100% miner weight until the next target is
  solved.

Keep prose, proof-efficiency, subjective judging, generated/hybrid scoring, and
commit-reveal out of the hot path unless the user explicitly reopens the
decision.

## Fork State

- Working checkout: `/Users/leehall/lemma-wta` for now.
- Fork base: `/Users/leehall/lemma` at `a95bff4`.
- Remote `upstream` points to `/Users/leehall/lemma`.
- Public CLI: `lemma`.
- Internal package: `lemma`.
- Default source: `LEMMA_PROBLEM_SOURCE=known_theorems`.
- Default ledger path: `~/.lemma/wta-ledger.jsonl`.
- Default submission store: `~/.lemma/submissions.json`.

## WTA Surfaces

- Manifest loader: `lemma/problems/known_theorems.py`.
- Vendored manifest: `lemma/problems/known_theorems_manifest.json`.
- Pending proof store: `lemma/submissions.py`.
- Ledger helpers: `lemma/wta.py`.
- Miner proof-serving flow: `lemma/miner/forward.py`.
- Validator WTA loop: `lemma/validator/epoch.py`.
- Public CLI:
  - `lemma target show`
  - `lemma target ledger`
  - `lemma submit --problem <target-id> --submission <Submission.lean>`
  - `lemma verify --problem <target-id> --submission <Submission.lean>`
  - `lemma miner start`
  - `lemma validator check`
  - `lemma validator start`
  - `lemma validator dry-run`
  - `lemma meta`

## Rules For Future Agents

- Preserve `proof_script` as the only reward-critical miner artifact.
- Do not add judge scoring, prose scoring, proof-efficiency scoring, or
  difficulty-weighted rewards to WTA.
- Preserve deterministic target order and deterministic tie handling.
- Treat the current manifest as smoke-test material, not final launch supply.
- Keep v1 launch targets to known mathematics with human proof references and
  duplicate-review attestation.
- Keep upstream attribution and source commit in manifest rows.
- Update README, CLI help, tests, and this file when the mechanism changes.
