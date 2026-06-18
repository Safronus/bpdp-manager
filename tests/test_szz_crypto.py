"""Testy šifrovaného kontejneru pro export/import cache SZZ (PBKDF2 + AES-GCM)."""

from __future__ import annotations

import pytest

from bpdpmanager.services.szz_crypto import decrypt, encrypt


def test_roundtrip() -> None:
    data = "tajná data — příliš žluťoučký kůň".encode()
    blob = encrypt(data, "heslo123")
    assert decrypt(blob, "heslo123") == data
    assert b"tajn" not in blob          # je opravdu zašifrované (ne plaintext)


def test_wrong_password_raises() -> None:
    blob = encrypt(b"x", "spravne")
    with pytest.raises(ValueError):
        decrypt(blob, "spatne")


def test_foreign_or_corrupt_raises() -> None:
    with pytest.raises(ValueError):
        decrypt(b'{"format":"neco-jineho"}', "h")   # cizí formát
    with pytest.raises(ValueError):
        decrypt(b"naprosty binarni nesmysl \x00\x01", "h")   # poškozený


def test_empty_password_rejected() -> None:
    with pytest.raises(ValueError):
        encrypt(b"x", "")


def test_salt_nonce_are_random() -> None:
    # stejná data + heslo → různý šifrotext (náhodná sůl i nonce)
    assert encrypt(b"same", "pw") != encrypt(b"same", "pw")
