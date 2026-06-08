"""Náprava prohozeného textu/přílohy + detekce plného textu ve STAG sekci."""

from __future__ import annotations

from pathlib import Path

import pytest

from bpdpmanager.models import Student, Thesis
from bpdpmanager.models.enums import AttachmentKind, ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.services.stag_api import StagFile, _refine_sections
from bpdpmanager.storage import JsonRepository


# ── detekce plného textu v sekci „el. podoba" ───────────────────────────────
def _mk(name: str) -> StagFile:
    return StagFile(soubidno="1", filename=name, download_path="p", section="elpodoba")


def _sections(files):
    _refine_sections(files)
    return [f.section for f in files]


def test_zip_before_pdf_pdf_is_text() -> None:
    files = [_mk("Golan_priloha.zip"), _mk("Golan_DP.pdf")]
    assert _sections(files) == ["appendix", "text"]


def test_pdf_before_zip_pdf_is_text() -> None:
    files = [_mk("Golan_DP.pdf"), _mk("Golan_priloha.zip")]
    assert _sections(files) == ["text", "appendix"]


def test_named_appendix_pdf_not_text() -> None:
    files = [_mk("Golan_DP.pdf"), _mk("Golan_prilohy.pdf")]
    assert _sections(files) == ["text", "appendix"]


def test_single_pdf_is_text() -> None:
    files = [_mk("Golan_DP.pdf")]
    assert _sections(files) == ["text"]


def test_bundle_only_zip_stays_text() -> None:
    """Jediný zip v „el. podobě" (balík text+přílohy) zůstane textem — není
    co povýšit na text, takže k prohození zip↔pdf nedojde."""
    files = [_mk("Golan_DP_kompletni.zip")]
    assert _sections(files) == ["text"]


def test_pdf_always_wins_over_earlier_zip() -> None:
    """I když zip přijde první, text práce je vždy PDF (žádné zip=text+pdf=příloha)."""
    files = [_mk("a_priloha.zip"), _mk("b_priloha.zip"), _mk("Golan_DP.pdf")]
    assert _sections(files) == ["appendix", "appendix", "text"]


# ── náprava existujících prohozených prací ──────────────────────────────────
@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


@pytest.fixture
def thesis(service: ThesisService) -> str:
    s = Student(first_name="Hugo", last_name="Golan")
    service.upsert_student(s)
    t = Thesis(type=ThesisType.DP, status=ThesisStatus.IN_PROGRESS,
               academic_year="2025/2026", student_id=s.id)
    service.upsert_thesis(t)
    return t.id


def _make_swapped(service, tid, tmp_path):
    z = tmp_path / "g.zip"
    z.write_bytes(b"PK" + b"X" * 2000)
    p = tmp_path / "g.pdf"
    p.write_bytes(b"%PDF-1.4" + b"Y" * 5000)
    service.attach_document(tid, z, kind=AttachmentKind.THESIS_TEXT, label="t.zip")
    service.attach_document(tid, p, kind=AttachmentKind.THESIS_APPENDIX, label="a.pdf")


def test_find_swapped_flags_archive_text_and_pdf_appendix(service, thesis, tmp_path):
    _make_swapped(service, thesis, tmp_path)
    swaps = service.find_swapped_documents()
    assert len(swaps) == 1
    assert swaps[0].work_id == thesis
    assert Path(swaps[0].text_url).suffix == ".zip"
    assert Path(swaps[0].appendix_url).suffix == ".pdf"


def test_find_swapped_ignores_correct_pdf_text(service, thesis, tmp_path):
    # text je PDF a příloha je zip → správně, nic k nápravě
    z = tmp_path / "g.zip"
    z.write_bytes(b"PK" + b"X" * 2000)
    p = tmp_path / "g.pdf"
    p.write_bytes(b"%PDF" + b"Y" * 5000)
    service.attach_document(thesis, p, kind=AttachmentKind.THESIS_TEXT, label="t.pdf")
    service.attach_document(thesis, z, kind=AttachmentKind.THESIS_APPENDIX, label="a.zip")
    assert service.find_swapped_documents() == []


def test_repair_swaps_kinds_renames_and_moves(service, thesis, tmp_path):
    _make_swapped(service, thesis, tmp_path)
    sw = service.find_swapped_documents()[0]
    n = service.repair_swapped_documents(
        [(sw.work_id, sw.is_opposing, sw.text_url, sw.appendix_url)]
    )
    assert n == 1
    atts = service.get_thesis(thesis).attachments
    text = [a for a in atts if a.kind == AttachmentKind.THESIS_TEXT]
    app = [a for a in atts if a.kind == AttachmentKind.THESIS_APPENDIX]
    assert len(text) == 1 and Path(text[0].url_or_path).suffix == ".pdf"
    assert len(app) == 1 and Path(app[0].url_or_path).suffix == ".zip"
    # soubory fyzicky existují na nových cestách, žádný osiřelý
    for a in atts:
        assert service.document_absolute_path(thesis, a).is_file()
    # idempotence — po opravě už nic
    assert service.find_swapped_documents() == []
