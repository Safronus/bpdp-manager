"""Šifrovaný kontejner pro export/import cache „Průběh SZZ".

Kvalitní symetrická kryptografie:
- **PBKDF2-HMAC-SHA256** (200k iterací) odvodí 256bitový klíč z hesla + náhodné
  soli — pomalé brute-force, žádné heslo se neukládá.
- **AES-256-GCM** = autentizované šifrování (důvěrnost + integrita); špatné heslo
  nebo poškozený soubor selžou ověřením (``InvalidTag``), nedešifruje se nesmysl.

Formát souboru je JSON obálka s base64 poli (salt, nonce, ciphertext) + verzí,
takže je dopředu rozšiřitelný a samopopisný.
"""

from __future__ import annotations

import base64
import json
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_MAGIC = "bpdpmanager-szz-export"
_VERSION = 1
_ITERATIONS = 200_000
_SALT_LEN = 16
_NONCE_LEN = 12      # doporučená délka nonce pro GCM
_KEY_LEN = 32        # AES-256
_AAD = _MAGIC.encode("utf-8")   # asociovaná data (autentizuje i formát)


def _derive_key(password: str, salt: bytes, iterations: int) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=_KEY_LEN,
                     salt=salt, iterations=iterations)
    return kdf.derive(password.encode("utf-8"))


def encrypt(plaintext: bytes, password: str) -> bytes:
    """``plaintext`` → JSON obálka (bytes) zašifrovaná heslem. Prázdné heslo = chyba."""
    if not password:
        raise ValueError("Heslo nesmí být prázdné.")
    salt = os.urandom(_SALT_LEN)
    nonce = os.urandom(_NONCE_LEN)
    key = _derive_key(password, salt, _ITERATIONS)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, _AAD)
    envelope = {
        "format": _MAGIC,
        "version": _VERSION,
        "kdf": "PBKDF2-HMAC-SHA256",
        "iterations": _ITERATIONS,
        "cipher": "AES-256-GCM",
        "salt": base64.b64encode(salt).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }
    return json.dumps(envelope, indent=2).encode("utf-8")


def decrypt(blob: bytes, password: str) -> bytes:
    """Obálka (bytes) + heslo → ``plaintext``. ``ValueError`` při špatném hesle /
    poškozeném či cizím souboru (nikdy nevrátí nesmysl — GCM ověří integritu)."""
    try:
        env = json.loads(blob.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise ValueError("Soubor není platný export (poškozený).") from e
    if not isinstance(env, dict) or env.get("format") != _MAGIC:
        raise ValueError("Soubor není export průběhu SZZ.")
    try:
        salt = base64.b64decode(env["salt"])
        nonce = base64.b64decode(env["nonce"])
        ciphertext = base64.b64decode(env["ciphertext"])
        iterations = int(env.get("iterations", _ITERATIONS))
    except (KeyError, ValueError, TypeError) as e:
        raise ValueError("Poškozený export (chybí/neplatná pole).") from e
    key = _derive_key(password, salt, iterations)
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, _AAD)
    except InvalidTag as e:
        raise ValueError("Špatné heslo nebo poškozený soubor.") from e
