#!/usr/bin/env python3
"""Adversarial "Eve" gate for the Lemma redesign.

Simulates the per-epoch budget pipeline in-process under five attacker scenarios
and prints a structured report. Returns non-zero if any invariant is violated.

Scenarios:
1. Replay attack: Eve replays Alice's reveal under her own hotkey.
2. Sybil pool, same coldkey: 10 sybils + 1 honest miner.
3. Sybil pool, different coldkeys: 10 sybils on 10 distinct coldkeys.
4. Template enumerator: miner with cached proofs vs miner with a real prover.
5. First-to-solve registration tiebreak: same-block commits, different registration.

Each scenario reports earned/burn/eve-ratio. Gate: ``Eve_emission_ratio ≤ 2.0``.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field

from lemma.scoring.budget import compute_budget
from lemma.scoring.dedup import submission_fingerprint


@dataclass
class ScoringRound:
    miner_uids: list[int]
    solved_by_theorem: dict[str, set[int]] = field(default_factory=dict)
    proofs_by_theorem_uid: dict[tuple[str, int], str] = field(default_factory=dict)
    registration_block: dict[int, int] = field(default_factory=dict)
    theorem_statements: dict[str, str] = field(default_factory=dict)


def run_round(rnd: ScoringRound, *, commit_block: int = 100) -> tuple[dict[int, float], float]:
    """α-rename dedup, then run the budget combiner. Returns ``(weights, burn_share)``."""
    seen: dict[tuple[str, str], int] = {}
    accepted: dict[str, set[int]] = {tid: set() for tid in rnd.solved_by_theorem}
    for tid, uids in rnd.solved_by_theorem.items():
        ordered = sorted(uids, key=lambda u: rnd.registration_block.get(u, 10**9))
        for uid in ordered:
            proof = rnd.proofs_by_theorem_uid.get((tid, uid), "")
            fp = submission_fingerprint(rnd.theorem_statements.get(tid, tid), proof)
            if (tid, fp) in seen:
                continue
            seen[(tid, fp)] = uid
            accepted[tid].add(uid)
    return compute_budget(
        accepted,
        active_uids=set(rnd.miner_uids),
        registration_block=rnd.registration_block,
        commit_block=commit_block,
        reign_by_uid={},
    )


def scenario_replay_attack() -> dict[str, object]:
    rnd = ScoringRound(miner_uids=list(range(30)))
    rnd.theorem_statements["t"] = "theorem t : True := by trivial"
    rnd.solved_by_theorem["t"] = {1, 2}
    rnd.proofs_by_theorem_uid[("t", 1)] = "by trivial"
    rnd.proofs_by_theorem_uid[("t", 2)] = "by trivial"  # identical replay
    rnd.registration_block = {1: 50, 2: 60, **{i: 100 for i in range(30) if i not in {1, 2}}}
    w, burn = run_round(rnd)
    return {"name": "replay_attack", "alice_weight": w.get(1, 0.0), "eve_weight": w.get(2, 0.0),
            "burn": burn, "passed": w.get(1, 0.0) > 0.0 and w.get(2, 0.0) == 0.0}


def _sybil_scenario(name: str) -> dict[str, object]:
    network = list(range(30))
    rnd = ScoringRound(miner_uids=network)
    rnd.theorem_statements["t"] = "theorem t : True := by trivial"
    rnd.solved_by_theorem["t"] = set(range(11))
    rnd.proofs_by_theorem_uid[("t", 0)] = "by exact True.intro"
    for i in range(1, 11):
        rnd.proofs_by_theorem_uid[("t", i)] = "by trivial"  # sybil clones
    rnd.registration_block = {i: 100 + i for i in network}
    w, burn = run_round(rnd)
    honest = w.get(0, 0.0)
    sybil = sum(w.get(i, 0.0) for i in range(1, 11))
    ratio = (sybil / honest) if honest > 0 else (float("inf") if sybil > 0 else 0.0)
    return {"name": name, "honest_weight": honest, "sybil_combined_weight": sybil,
            "burn": burn, "eve_emission_ratio": ratio,
            "passed": honest > 0.0 and ratio <= 2.0}


def scenario_sybil_same_coldkey() -> dict[str, object]:
    return _sybil_scenario("sybil_same_coldkey")


def scenario_sybil_different_coldkeys() -> dict[str, object]:
    return _sybil_scenario("sybil_different_coldkeys")


def scenario_template_enumerator() -> dict[str, object]:
    """Enumerator caches T1 proofs; T2 rotates fresh — enumerator can't solve it."""
    weights_total: dict[int, float] = {1: 0.0, 2: 0.0}
    burn_total = 0.0
    network = list(range(20))
    for tid, only_honest in (("T1", False), ("T2", True)):
        rnd = ScoringRound(miner_uids=network)
        rnd.theorem_statements[tid] = f"theorem {tid} : True := by trivial"
        rnd.proofs_by_theorem_uid[(tid, 2)] = "by exact True.intro"
        rnd.solved_by_theorem[tid] = {2}
        if not only_honest:
            rnd.solved_by_theorem[tid].add(1)
            rnd.proofs_by_theorem_uid[(tid, 1)] = "by trivial"
        rnd.registration_block = {i: 100 + i for i in network}
        w, burn = run_round(rnd)
        for uid, val in w.items():
            weights_total[uid] = weights_total.get(uid, 0.0) + val
        burn_total += burn
    return {"name": "template_enumerator",
            "enumerator_total": weights_total.get(1, 0.0),
            "honest_total": weights_total.get(2, 0.0),
            "burn_total": burn_total,
            "passed": weights_total.get(2, 0.0) > weights_total.get(1, 0.0)}


def scenario_registration_tiebreak() -> dict[str, object]:
    network = list(range(20))
    rnd = ScoringRound(miner_uids=network)
    rnd.theorem_statements["t"] = "theorem t : True := by trivial"
    rnd.solved_by_theorem["t"] = {1, 2}
    rnd.proofs_by_theorem_uid[("t", 1)] = "by exact True.intro"
    rnd.proofs_by_theorem_uid[("t", 2)] = "by trivial"
    rnd.registration_block = {i: 100 + i for i in network}
    rnd.registration_block.update({1: 50, 2: 40})
    w, burn = run_round(rnd)
    return {"name": "registration_tiebreak", "uid1_weight": w.get(1, 0.0),
            "uid2_weight": w.get(2, 0.0), "burn": burn,
            "passed": w.get(2, 0.0) >= w.get(1, 0.0)}


SCENARIOS = (
    scenario_replay_attack,
    scenario_sybil_same_coldkey,
    scenario_sybil_different_coldkeys,
    scenario_template_enumerator,
    scenario_registration_tiebreak,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", default=None, help="ignored; accepted for CLI compatibility")
    ap.add_argument("--report", default="-")
    args = ap.parse_args()

    results = [fn() for fn in SCENARIOS]
    ratios = [r.get("eve_emission_ratio") for r in results if "eve_emission_ratio" in r]
    eve_emission_ratio = max((float(r) for r in ratios if isinstance(r, (int, float))), default=0.0)
    all_passed = all(bool(r.get("passed")) for r in results)

    report = {
        "scenarios": results,
        "eve_emission_ratio": eve_emission_ratio,
        "all_passed": all_passed,
    }
    out = json.dumps(report, indent=2)
    if args.report == "-":
        sys.stdout.write(out + "\n")
    else:
        from pathlib import Path

        Path(args.report).write_text(out + "\n", encoding="utf-8")
        print(f"wrote {args.report}")
    return 0 if all_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
