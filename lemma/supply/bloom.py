"""Minimal byte-array bloom filter for the public-corpus freshness gate.

File format::

    "LEMMA_BLOOM" (11 bytes magic)
    "\x01"        (1 byte version)
    8 bytes u64-le: bit_count
    4 bytes u32-le: hash_count
    bit_count/8 bytes: bitmap
"""

from __future__ import annotations

import hashlib
import math
import struct
from pathlib import Path

_MAGIC = b"LEMMA_BLOOM"
_VERSION = 1


class BloomFilter:
    __slots__ = ("bit_count", "hash_count", "bitmap")

    def __init__(self, bit_count: int, hash_count: int, bitmap: bytearray | None = None) -> None:
        self.bit_count = max(8, int(bit_count))
        self.hash_count = max(1, int(hash_count))
        self.bitmap = bitmap if bitmap is not None else bytearray((self.bit_count + 7) // 8)

    @classmethod
    def for_capacity(cls, expected_items: int, fp_rate: float = 0.001) -> BloomFilter:
        n = max(1, int(expected_items))
        p = max(1e-9, min(0.5, float(fp_rate)))
        bits = max(8, int(-(n * math.log(p)) / (math.log(2) ** 2)))
        k = max(1, int(round((bits / n) * math.log(2))))
        return cls(bit_count=bits, hash_count=k)

    def _bits(self, key: bytes) -> list[int]:
        digest = hashlib.sha256(key).digest()
        h1 = int.from_bytes(digest[:8], "big")
        h2 = int.from_bytes(digest[8:16], "big") or 1
        return [(h1 + i * h2) % self.bit_count for i in range(self.hash_count)]

    def add(self, key: bytes) -> None:
        for b in self._bits(key):
            self.bitmap[b >> 3] |= 1 << (b & 7)

    def __contains__(self, key: bytes) -> bool:
        return all((self.bitmap[b >> 3] >> (b & 7)) & 1 for b in self._bits(key))

    def to_bytes(self) -> bytes:
        return _MAGIC + bytes([_VERSION]) + struct.pack("<QI", self.bit_count, self.hash_count) + bytes(self.bitmap)

    @classmethod
    def from_bytes(cls, blob: bytes) -> BloomFilter:
        if not blob.startswith(_MAGIC):
            raise ValueError("not a lemma bloom file")
        if blob[len(_MAGIC)] != _VERSION:
            raise ValueError(f"unsupported bloom version: {blob[len(_MAGIC)]}")
        off = len(_MAGIC) + 1
        bit_count, hash_count = struct.unpack("<QI", blob[off:off + 12])
        off += 12
        bytes_needed = (bit_count + 7) // 8
        return cls(bit_count=bit_count, hash_count=hash_count, bitmap=bytearray(blob[off:off + bytes_needed]))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.to_bytes())

    @classmethod
    def load(cls, path: Path) -> BloomFilter | None:
        if not path.is_file():
            return None
        try:
            return cls.from_bytes(path.read_bytes())
        except (ValueError, OSError):
            return None
