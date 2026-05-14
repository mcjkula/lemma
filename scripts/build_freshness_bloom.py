#!/usr/bin/env python3
"""Build ``data/freshness_bloom.bin`` from public-corpus Lean sources.

Usage::

    python scripts/build_freshness_bloom.py \\
        --root path/to/corpus_a \\
        --root path/to/corpus_b \\
        --out data/freshness_bloom.bin

Rebuild monthly. The validator loads the file at startup; candidate theorems
whose normalised hash is in the bloom are rejected by the freshness gate.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from lemma.supply.bloom import BloomFilter
from lemma.supply.freshness import statement_hash

_THEOREM_RE = re.compile(
    r"\b(?:theorem|lemma|example)\s+(\S+)\s*[\s\S]+?:=", re.MULTILINE,
)


def _extract_statements(text: str) -> list[str]:
    """Coarse: grab every `theorem/lemma/example NAME ... :=` head as a normalised statement."""
    out: list[str] = []
    for m in _THEOREM_RE.finditer(text):
        head = text[m.start():m.end()]
        out.append(head)
    return out


def ingest(root: Path) -> list[str]:
    statements: list[str] = []
    for p in root.rglob("*.lean"):
        try:
            statements.extend(_extract_statements(p.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    return statements


def main() -> int:
    ap = argparse.ArgumentParser(description="Build public-corpus freshness bloom filter")
    ap.add_argument("--root", action="append", default=[], help="path to a Lean corpus (repeatable)")
    ap.add_argument("--out", type=Path, default=Path("data/freshness_bloom.bin"))
    ap.add_argument("--fp-rate", type=float, default=0.001)
    args = ap.parse_args()

    if not args.root:
        print("warning: no --root given; producing an empty bloom (operators must rebuild monthly)")

    statements: list[str] = []
    for r in args.root:
        statements.extend(ingest(Path(r).expanduser().resolve()))
    bf = BloomFilter.for_capacity(max(1024, len(statements) * 2), fp_rate=args.fp_rate)
    for s in statements:
        bf.add(statement_hash(s).encode("utf-8"))
    bf.save(args.out)
    print(f"wrote bloom: {args.out} ({len(statements)} statements, bits={bf.bit_count}, k={bf.hash_count})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
