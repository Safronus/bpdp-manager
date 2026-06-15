"""Indikátor připojení ke STAG — lehký ping `stag_api.check_reachable`."""

from __future__ import annotations

import urllib.error
import urllib.request

from bpdpmanager.services import stag_api


class _FakeResp:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_check_reachable_success(monkeypatch) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _FakeResp())
    ok, detail = stag_api.check_reachable(1.0)
    assert ok and detail == ""


def test_check_reachable_httperror_counts_as_up(monkeypatch) -> None:
    def boom(*a, **k):
        raise urllib.error.HTTPError("https://stag.utb.cz", 403, "Forbidden",
                                     None, None)

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    ok, _ = stag_api.check_reachable(1.0)
    assert ok   # server odpověděl (403) → spojení i TLS funguje


def test_check_reachable_offline(monkeypatch) -> None:
    def boom(*a, **k):
        raise urllib.error.URLError("no route to host")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    ok, detail = stag_api.check_reachable(1.0)
    assert not ok and "nedostupný" in detail
