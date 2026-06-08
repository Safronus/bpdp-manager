"""Stažení českého slovníku do uživatelského adresáře (mockovaná síť)."""

from __future__ import annotations

from unittest import mock

import pytest

import bpdpmanager.services.spellcheck as sc


class _FakeResp:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


def test_download_writes_user_dictionary() -> None:
    # autouse fixture isoluje ~/.bpdpmanager → app_data_dir je tmp
    payload = {".aff": b"A" * 2000, ".dic": b"D" * 5000}

    def fake_urlopen(req, timeout=None, context=None):
        suffix = ".aff" if req.full_url.endswith(".aff") else ".dic"
        return _FakeResp(payload[suffix])

    with mock.patch(
        "bpdpmanager.services.spellcheck.urllib.request.urlopen",
        side_effect=fake_urlopen,
    ):
        sc.download_dictionary()

    base = sc._user_base()
    assert base.with_suffix(".aff").read_bytes() == payload[".aff"]
    assert base.with_suffix(".dic").read_bytes() == payload[".dic"]


def test_download_rejects_truncated_file() -> None:
    with mock.patch(
        "bpdpmanager.services.spellcheck.urllib.request.urlopen",
        return_value=_FakeResp(b"tiny"),
    ):
        with pytest.raises(RuntimeError):
            sc.download_dictionary()
    # nesmí zůstat poloviční slovník
    assert not sc._user_base().with_suffix(".aff").exists()


def test_download_network_error_wrapped() -> None:
    import urllib.error

    with mock.patch(
        "bpdpmanager.services.spellcheck.urllib.request.urlopen",
        side_effect=urllib.error.URLError("nope"),
    ):
        with pytest.raises(RuntimeError):
            sc.download_dictionary()


def test_can_download_reflects_spylls() -> None:
    # spylls je v dev prostředí nainstalovaný
    assert sc.can_download() is sc.spylls_installed()
