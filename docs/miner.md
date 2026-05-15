# Miner

## What the miner does

The bundled miner is a **reference FastAPI service** behind Epistula-signed HTTP.
It exposes one endpoint that validators hit:

```
POST /lemma/reveal
  body: {theorem_id, metronome_id, proof_script}
  reply: {accepted, reason}
```

The miner does **not** ship a prover. Operators plug in their own solver and pass
it to `lemma.miner.service.build_app(wallet, solver=...)`. The default solver
returns an empty proof — useful for axon smoke tests, useless for earning.

Walkthrough: [getting-started.md](getting-started.md).

## Run

```bash
uv run lemma miner start
```

Set `AXON_PORT`, `AXON_EXTERNAL_IP` (or `AXON_DISCOVER_EXTERNAL_IP=true`), and
wallet names in `.env`. The miner registers its axon URL on chain via
`serve_extrinsic` at startup and then serves HTTP on `AXON_PORT`.

## Seeing replies and Lean status

Validators decide whether your proof typechecks; the miner process does not
receive scores back on the axon path.

- When a validator forward arrives, your solver is invoked once with the
  `ChallengePayload`. Whatever string it returns is sent back as the
  `proof_script` in `/lemma/reveal`.
- Final validator weights land on chain via `set_weights`. Use
  `uv run btcli subnet show --netuid 467 --network test` to inspect your UID's
  incentive.

## Compose

```bash
docker compose -f docker-compose.yml up miner
```

## Output contract

`proof_script` must be complete `Submission.lean` content (with the
`namespace Submission … end Submission` block) for the challenge theorem name.

The validator's Lean sandbox runs `lake build Submission` and `lake env lean
AxiomCheck.lean`; only proofs that depend exclusively on
`{propext, Quot.sound, Classical.choice}` count as solves.
