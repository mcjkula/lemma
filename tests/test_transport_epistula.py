"""Epistula sign/verify roundtrip."""

from __future__ import annotations

import time

import pytest
from bittensor_wallet import Keypair

from lemma.transport.epistula import ReplayCache, sign, verify


def _kp() -> tuple[Keypair, Keypair]:
    sender = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
    receiver = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
    return sender, receiver


def test_roundtrip_accepts_signed_body() -> None:
    sender, receiver = _kp()
    body = b'{"theorem_id":"gen/1","proof_script":"by trivial"}'
    headers = sign(keypair=sender, body=body, signed_for_ss58=receiver.ss58_address)
    out = verify(
        headers=headers,
        body=body,
        receiver_ss58=receiver.ss58_address,
        replay_cache=ReplayCache(),
    )
    assert out.ok, out.reason


def test_tampered_body_rejected() -> None:
    sender, receiver = _kp()
    body = b"x"
    headers = sign(keypair=sender, body=body, signed_for_ss58=receiver.ss58_address)
    out = verify(
        headers=headers,
        body=b"y",
        receiver_ss58=receiver.ss58_address,
        replay_cache=ReplayCache(),
    )
    assert not out.ok
    assert out.reason == "bad_signature"


def test_replayed_nonce_rejected() -> None:
    sender, receiver = _kp()
    body = b"hi"
    headers = sign(keypair=sender, body=body, signed_for_ss58=receiver.ss58_address)
    cache = ReplayCache()
    a = verify(headers=headers, body=body, receiver_ss58=receiver.ss58_address, replay_cache=cache)
    b = verify(headers=headers, body=body, receiver_ss58=receiver.ss58_address, replay_cache=cache)
    assert a.ok
    assert not b.ok
    assert b.reason == "replayed_nonce"


def test_stale_timestamp_rejected() -> None:
    sender, receiver = _kp()
    body = b"hi"
    old_ts = int(time.time() * 1000) - 600_000
    headers = sign(
        keypair=sender,
        body=body,
        signed_for_ss58=receiver.ss58_address,
        timestamp_ms=old_ts,
    )
    out = verify(
        headers=headers,
        body=body,
        receiver_ss58=receiver.ss58_address,
        replay_cache=ReplayCache(),
    )
    assert not out.ok
    assert out.reason == "stale_timestamp"


def test_wrong_receiver_rejected() -> None:
    sender, receiver = _kp()
    other = Keypair.create_from_mnemonic(Keypair.generate_mnemonic())
    body = b"hi"
    headers = sign(keypair=sender, body=body, signed_for_ss58=receiver.ss58_address)
    out = verify(
        headers=headers,
        body=body,
        receiver_ss58=other.ss58_address,
        replay_cache=ReplayCache(),
    )
    assert not out.ok
    assert out.reason == "wrong_receiver"
