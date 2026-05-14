"""Freshness gate: on-chain seen registry + off-chain public-corpus bloom filter."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from lemma.supply.bloom import BloomFilter


def _normalize_statement(text: str) -> str:
    no_block = re.sub(r"/-[\s\S]*?-/", "", text or "")
    no_line = re.sub(r"--[^\n]*", "", no_block)
    return re.sub(r"\s+", " ", no_line).strip()


def statement_hash(text: str) -> str:
    return hashlib.sha256(_normalize_statement(text).encode("utf-8")).hexdigest()


class FreshnessRegistry:
    def __init__(self, store_path: Path | None = None, public_corpus_bloom: Path | None = None) -> None:
        self._store_path = store_path
        self._seen: set[str] = set()
        if store_path and store_path.is_file():
            for line in store_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self._seen.add(line.strip())
        self._bloom = BloomFilter.load(public_corpus_bloom) if public_corpus_bloom else None

    def is_fresh(self, text: str) -> bool:
        h = statement_hash(text)
        if h in self._seen:
            return False
        if self._bloom is not None and h.encode("utf-8") in self._bloom:
            return False
        return True

    def record(self, text: str) -> None:
        h = statement_hash(text)
        if h in self._seen:
            return
        self._seen.add(h)
        if self._store_path is None:
            return
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        with self._store_path.open("a", encoding="utf-8") as f:
            f.write(f"{h}\n")
