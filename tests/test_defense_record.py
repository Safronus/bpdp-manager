"""Testy typu přílohy „Soubor s průběhem obhajoby" (detekce + přeřazení)."""

from __future__ import annotations

from pathlib import Path

import pytest

from bpdpmanager.models import Attachment, OpposingThesis, Student, Thesis
from bpdpmanager.models.enums import AttachmentKind, ThesisStatus, ThesisType
from bpdpmanager.services import ThesisService
from bpdpmanager.services.stag_api import (
    StagFile,
    _refine_sections,
    is_defense_record_filename,
)
from bpdpmanager.storage import JsonRepository


@pytest.fixture
def service(tmp_path: Path) -> ThesisService:
    repo = JsonRepository(path=tmp_path / "db.json", backup_path=tmp_path / "db.json.bak")
    return ThesisService(repo)


@pytest.mark.parametrize(
    "name,expected",
    [
        ("obhajoba_19.pdf", True),
        ("09_Bereznaj_zapis_o_statni_zaverecne_zkousky.pdf", True),
        ("protokol_o_obhajobe.pdf", True),
        ("Zaznam o obhajobě.pdf", True),
        ("fulltext.pdf", False),
        ("Novak_posudek-oponenta.doc", False),
        ("prilohy.zip", False),
        ("prezentace.pptx", False),
    ],
)
def test_is_defense_record_filename(name: str, expected: bool) -> None:
    assert is_defense_record_filename(name) is expected


def test_refine_sections_marks_defense_record() -> None:
    files = [
        StagFile(soubidno="1", filename="obhajoba_10.pdf", download_path="/a",
                 section="other"),
        StagFile(soubidno="2", filename="cosi.pdf", download_path="/b", section="other"),
    ]
    _refine_sections(files)
    assert files[0].section == "defense_record"
    assert files[1].section == "other"


def test_section_to_kind_has_defense_record() -> None:
    from bpdpmanager.ui.stag_import_dialog import _SECTION_TO_KIND

    assert _SECTION_TO_KIND["defense_record"] == AttachmentKind.DEFENSE_RECORD


def test_pair_other_with_stag() -> None:
    """Spárování lokálních „Jiné" se STAG soubory + odhad průběhu obhajoby."""
    from types import SimpleNamespace

    from bpdpmanager.ui.defense_reclassify_dialog import pair_other_with_stag

    local = [SimpleNamespace(label="Novak_jine_2026.pdf"),
             SimpleNamespace(label="Svoboda_jine_2026.pdf")]
    stag = [
        StagFile(soubidno="1", filename="fulltext.pdf", download_path="/a",
                 section="text"),
        StagFile(soubidno="2", filename="obhajoba_19.pdf", download_path="/b",
                 section="defense_record"),
        StagFile(soubidno="3", filename="dokument.pdf", download_path="/c",
                 section="other"),
    ]
    pairs = pair_other_with_stag(local, stag)
    assert len(pairs) == 2
    # 1. lokální ↔ obhajoba_19.pdf (defense, předzaškrtnuto).
    assert pairs[0][1] == "obhajoba_19.pdf" and pairs[0][2] is True
    # 2. lokální ↔ dokument.pdf (generický název → odhad False, ale dohledán název).
    assert pairs[1][1] == "dokument.pdf" and pairs[1][2] is False


def test_reclassify_defense_records(service: ThesisService) -> None:
    s = Student(first_name="Jan", last_name="Novák")
    service.upsert_student(s)
    t = Thesis(
        type=ThesisType.BP, status=ThesisStatus.DEFENDED, academic_year="2024/2025",
        student_id=s.id,
        attachments=[
            Attachment(label="obhajoba_19.pdf", url_or_path="x/obhajoba_19.pdf",
                       kind=AttachmentKind.OTHER, is_file=True),
            Attachment(label="poznamky.txt", url_or_path="x/poznamky.txt",
                       kind=AttachmentKind.OTHER, is_file=True),
        ],
    )
    service.upsert_thesis(t)
    op = OpposingThesis(
        type=ThesisType.DP, academic_year="2024/2025", student_last_name="Dvořák",
        attachments=[
            Attachment(label="05_Dvorak_zapis_o_statni_zaverecne_zkousky.pdf",
                       url_or_path="y/z.pdf", kind=AttachmentKind.OTHER, is_file=True),
        ],
    )
    service.upsert_opposing_thesis(op)

    # Dry-run: 2 kandidáti, data beze změny.
    candidates = service.reclassify_defense_records(dry_run=True)
    assert len(candidates) == 2
    assert service.get_thesis(t.id).attachments[0].kind == AttachmentKind.OTHER

    # Ostrý běh: přeřadí jen odpovídající, ostatní „Jiné" nechá.
    applied = service.reclassify_defense_records()
    assert len(applied) == 2
    ts = service.get_thesis(t.id)
    assert ts.attachments[0].kind == AttachmentKind.DEFENSE_RECORD
    assert ts.attachments[1].kind == AttachmentKind.OTHER
    opp = service.get_opposing_thesis(op.id)
    assert opp.attachments[0].kind == AttachmentKind.DEFENSE_RECORD
