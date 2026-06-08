"""Systémový tisk PDF přes CUPS ``lp`` (sestavení příkazu, chyby)."""

from __future__ import annotations

from unittest import mock

import pytest

from bpdpmanager.services import system_print

_RUN = "bpdpmanager.services.system_print.subprocess.run"
_AVAIL = "bpdpmanager.services.system_print.system_print_available"


def _ok_run():
    return mock.Mock(returncode=0, stdout="request id is P-1", stderr="")


def test_lp_command_duplex_and_copies(tmp_path) -> None:
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF")
    with mock.patch(_AVAIL, return_value=True), mock.patch(_RUN) as run:
        run.return_value = _ok_run()
        system_print.print_pdf(pdf, "Printer_X", duplex=True, copies=3)
    cmd = run.call_args[0][0]
    assert cmd[:3] == ["lp", "-d", "Printer_X"]
    assert "-n" in cmd and "3" in cmd
    assert "sides=two-sided-long-edge" in cmd
    assert str(pdf) == cmd[-1]


def test_lp_command_one_sided(tmp_path) -> None:
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF")
    with mock.patch(_AVAIL, return_value=True), mock.patch(_RUN) as run:
        run.return_value = _ok_run()
        system_print.print_pdf(pdf, "P", duplex=False)
    assert "sides=one-sided" in run.call_args[0][0]


def test_nonzero_return_raises(tmp_path) -> None:
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF")
    with mock.patch(_AVAIL, return_value=True), mock.patch(_RUN) as run:
        run.return_value = mock.Mock(returncode=1, stdout="", stderr="no such printer")
        with pytest.raises(RuntimeError, match="no such printer"):
            system_print.print_pdf(pdf, "P")


def test_missing_file_raises() -> None:
    with pytest.raises(RuntimeError):
        system_print.print_pdf("/does/not/exist.pdf", "P")


def test_no_printer_raises(tmp_path) -> None:
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF")
    with pytest.raises(RuntimeError):
        system_print.print_pdf(pdf, "")


def test_unavailable_raises(tmp_path) -> None:
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF")
    with mock.patch(_AVAIL, return_value=False):
        with pytest.raises(RuntimeError):
            system_print.print_pdf(pdf, "P")
