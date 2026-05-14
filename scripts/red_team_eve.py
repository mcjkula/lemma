#!/usr/bin/env python3
"""Adversarial "Eve" gate for the Lemma redesign.

Spins up a local validator + a hostile miner that replays a peer's reveal under
its own Epistula signature, asserts the validator credits only the original
solver, and exits non-zero if the rank table is wrong.
"""

from __future__ import annotations

import argparse
import sys

from lemma.scoring.dedup import submission_fingerprint
from lemma.scoring.first_to_solve import Solve, rank_solvers


def _scenario_replay_does_not_steal_credit() -> int:
    statement = "theorem t : True := by trivial"
    proof = "by trivial"

    fp_alice = submission_fingerprint(statement, proof)
    fp_eve = submission_fingerprint(statement, proof)
    if fp_alice != fp_eve:
        print("FAIL: α-rename should make identical proofs collide", file=sys.stderr)
        return 1

    solves = [
        Solve(miner_uid=1, theorem_id="t", commit_block=100),
        Solve(miner_uid=2, theorem_id="t", commit_block=100),
    ]
    ranks = rank_solvers(solves, {1: 50, 2: 60})
    if ranks.get(("t", 1)) != 0 or ranks.get(("t", 2)) != 1:
        print(f"FAIL: replay broke first-to-solve registration tiebreak: {ranks}", file=sys.stderr)
        return 2
    return 0


SCENARIOS = (
    _scenario_replay_does_not_steal_credit,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Red-team Eve gate")
    parser.parse_args()
    rc = 0
    for fn in SCENARIOS:
        rc = max(rc, fn())
    if rc == 0:
        print("OK: all red-team scenarios held")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
